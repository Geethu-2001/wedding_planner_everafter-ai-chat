from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st
from sqlalchemy import select

from wedding_planner.db import SessionLocal
from wedding_planner.models import (
    User, Wedding, WeddingMember, WeddingService, Vendor, Expense, WeddingTask
)
from wedding_planner.services.auth_service import register_user, authenticate_user
from wedding_planner.services.wedding_service import create_wedding
from wedding_planner.services.budget_service import budget_summary
from wedding_planner.services.pdf_service import generate_wedding_pdf
from wedding_planner.services.email_service import allowed_recipients, send_wedding_pdf
from wedding_planner.agents.graph import research_category

CATEGORIES = [
    "Wedding venue", "Photography", "Videography", "Catering", "Kerala sadya",
    "Decoration", "Floral decoration", "Lighting", "Bridal makeup", "Groom grooming",
    "Mehendi", "Cake", "Music and DJs", "Live bands", "Wedding planner",
    "Hotels and accommodation", "Transportation", "Invitations", "Return gifts",
    "Wedding outfits",
]
STATUSES = ["not_selected", "shortlisted", "selected", "quotation_received", "booked"]
STATUS_LABELS = {
    "not_selected": "Not selected", "shortlisted": "Shortlisted",
    "selected": "Selected", "quotation_received": "Quotation received", "booked": "Booked",
}


def _money(value):
    return f"₹{Decimal(value or 0):,.0f}"


def _safe_link(url):
    return urlparse(url or "").scheme in {"http", "https"}


def auth():
    st.title("EverAfter AI")
    st.caption("Plan together. Compare confidently. Keep every decision in one place.")
    login, signup = st.tabs(["Log in", "Create account"])
    with SessionLocal() as db:
        with login:
            email = st.text_input("Email address", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Log in", type="primary"):
                try:
                    user = authenticate_user(db, email, password)
                    if user:
                        st.session_state.user_id = user.id
                        st.rerun()
                    st.error("Email or password is incorrect.")
                except Exception as exc:
                    st.error(str(exc))
        with signup:
            name = st.text_input("Full name", key="signup_name")
            email = st.text_input("Email address", key="signup_email")
            role = st.selectbox("Your role", ["Bride", "Groom", "Partner", "Family"])
            password = st.text_input("Create password (10+ characters)", type="password", key="signup_password")
            if st.button("Create account", type="primary"):
                try:
                    user = register_user(db, name, email, password, role)
                    st.session_state.user_id = user.id
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))


def _create_project(db, user):
    st.header("Create your wedding workspace")
    with st.form("create_wedding_project"):
        col1, col2 = st.columns(2)
        bride = col1.text_input("Bride's name")
        groom = col2.text_input("Groom's name")
        wedding_date = st.date_input("Wedding date", value=None, format="YYYY-MM-DD")
        city = col1.text_input("City", value="Kochi")
        state = col2.text_input("State", value="Kerala")
        guests = st.number_input("Expected guests", min_value=1, max_value=100000, value=300)
        budget = st.number_input("Total budget (INR)", min_value=0.0, value=1500000.0, step=50000.0)
        style = st.selectbox("Wedding style", ["Traditional", "Modern", "Classic", "Minimal", "Luxury", "Fusion"])
        wedding_type = st.selectbox("Wedding type", ["Hindu", "Christian", "Muslim", "Interfaith", "Other"])
        submitted = st.form_submit_button("Create wedding project", type="primary")
    if submitted:
        try:
            fields = dict(bride_name=bride, groom_name=groom, city=city, state=state,
                          guest_count=int(guests), total_budget=budget,
                          wedding_style=style, wedding_type=wedding_type)
            if wedding_date:
                fields["wedding_date"] = wedding_date
            create_wedding(db, user, **fields)
            st.success("Wedding workspace created.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def _persist_research_result(db, wedding_id, category, result):
    url = result.get("url", "")
    title = result.get("title") or "Untitled provider"
    existing = db.scalars(select(Vendor).where(
        Vendor.wedding_id == wedding_id,
        Vendor.category == category,
        Vendor.source_url == url,
    )).first() if url else None
    if existing:
        existing.name = title
        existing.description = result.get("content", "")
        existing.price_text = result.get("price_text", "Not published — request a quotation")
        existing.result_summary = result.get("content", "")
        return existing
    vendor = Vendor(
        wedding_id=wedding_id, category=category, name=title,
        location="", description=result.get("content", ""),
        result_summary=result.get("content", ""), source_url=url,
        price_text=result.get("price_text", "Not published — request a quotation"),
        package_details="Not verified — contact provider for package inclusions",
        contact_details="Not found in search result",
        research_status="lead", selection_status="not_selected",
    )
    db.add(vendor)
    return vendor


def _research_tab(db, wedding):
    st.subheader("Find a venue or wedding service")
    st.write("Research one category at a time. Search results are saved to this wedding workspace so you can compare and decide later.")
    category = st.selectbox("What are you looking for?", CATEGORIES, key="research_category")
    col1, col2 = st.columns(2)
    city = col1.text_input("Search location", value=f"{wedding.city}, {wedding.state}")
    requirements = col2.text_input("Extra requirements", placeholder="e.g. 400 guests, outdoor, traditional Kerala style")
    if st.button("Search providers", type="primary"):
        with st.spinner(f"Researching {category.lower()} options..."):
            try:
                results = research_category(
                    category=category,
                    requirements=requirements,
                    location=city,
                    budget_summary={"total_budget_inr": str(wedding.total_budget),
                                    "guest_count": wedding.guest_count},
                )
                found = results.get("venue_results", []) + results.get("vendor_results", [])
                if not found:
                    st.warning("No results were returned. Check your Tavily API key and try a more specific search.")
                else:
                    for result in found:
                        _persist_research_result(db, wedding.id, category, result)
                    db.commit()
                    st.session_state.last_research_category = category
                    st.success(f"Saved {len(found)} research results under {category}.")
                for error in results.get("errors", []):
                    st.warning(error)
                if results.get("plan"):
                    st.info(results["plan"])
            except Exception as exc:
                st.error(f"Research could not be completed: {exc}")
    st.divider()
    st.subheader("Your researched options")
    rows = db.scalars(select(Vendor).where(
        Vendor.wedding_id == wedding.id,
        Vendor.category == category,
    ).order_by(Vendor.researched_at.desc())).all()
    if not rows:
        st.info("No providers saved for this category yet. Run a search above.")
    for vendor in rows:
        with st.container(border=True):
            left, right = st.columns([4, 1])
            left.markdown(f"**{vendor.name}**")
            left.caption(f"{vendor.category} · {vendor.location or city}")
            left.write(vendor.description or "No description was returned.")
            left.markdown(f"**Price:** {vendor.price_text or 'Not published — request a quotation'}")
            if vendor.source_url and _safe_link(vendor.source_url):
                left.link_button("Open original source", vendor.source_url)
            else:
                left.caption("No source URL was returned.")
            right.metric("Decision", STATUS_LABELS.get(vendor.selection_status, vendor.selection_status))
            new_status = right.selectbox(
                "Update status", STATUSES,
                index=STATUSES.index(vendor.selection_status) if vendor.selection_status in STATUSES else 0,
                key=f"status_{vendor.id}",
                format_func=lambda value: STATUS_LABELS[value],
            )
            if new_status != vendor.selection_status:
                vendor.selection_status = new_status
                db.commit()
                st.rerun()
            with st.expander("Provider details, quotation and notes"):
                st.write("**Search summary**")
                st.write(vendor.result_summary or vendor.description or "Not available")
                st.write("**Package details**")
                st.write(vendor.package_details or "Not verified. Ask the provider for a written package.")
                st.write("**Contact details**")
                st.write(vendor.contact_details or "Not found. Use the source website to contact the provider.")
                with st.form(f"vendor_details_{vendor.id}"):
                    package = st.text_area("Package / inclusions (enter verified details)", value=vendor.package_details or "")
                    contact = st.text_input("Contact details", value=vendor.contact_details or "")
                    quote = st.number_input("Quoted amount (INR; leave 0 if not received)", min_value=0.0,
                                            value=float(vendor.quoted_amount or 0), step=1000.0)
                    notes = st.text_area("Your notes", value=vendor.notes or "")
                    if st.form_submit_button("Save provider details"):
                        vendor.package_details = package
                        vendor.contact_details = contact
                        vendor.quoted_amount = quote if quote > 0 else None
                        vendor.notes = notes
                        if quote > 0 and vendor.selection_status in {"selected", "shortlisted"}:
                            vendor.selection_status = "quotation_received"
                        db.commit()
                        st.success("Provider details saved.")
                        st.rerun()


def _my_choices_tab(db, wedding):
    st.subheader("My wedding choices")
    rows = db.scalars(select(Vendor).where(
        Vendor.wedding_id == wedding.id,
        Vendor.selection_status.in_(["shortlisted", "selected", "quotation_received", "booked"]),
    ).order_by(Vendor.category, Vendor.name)).all()
    if not rows:
        st.info("Your shortlisted and selected providers will appear here.")
        return
    for row in rows:
        with st.container(border=True):
            a, b = st.columns([4, 1])
            a.markdown(f"**{row.category}: {row.name}**")
            a.write(STATUS_LABELS.get(row.selection_status, row.selection_status))
            if row.quoted_amount:
                a.write(f"Quotation: {_money(row.quoted_amount)}")
            else:
                a.write("Quotation: Not received")
            if row.source_url and _safe_link(row.source_url):
                a.link_button("View source", row.source_url)
            new_status = b.selectbox("Status", STATUSES,
                index=STATUSES.index(row.selection_status),
                key=f"choice_{row.id}", format_func=lambda x: STATUS_LABELS[x])
            if new_status != row.selection_status:
                row.selection_status = new_status
                db.commit()
                st.rerun()
    quoted_total = sum((Decimal(row.quoted_amount or 0) for row in rows), Decimal("0"))
    st.metric("Total of recorded quotations", _money(quoted_total))
    st.caption("This total includes only quotations you entered. Unpublished prices are not estimated.")


def _budget_tab(db, wedding, user_id):
    summary = budget_summary(db, wedding.id, user_id)
    c1, c2, c3 = st.columns(3)
    c1.metric("Total budget", _money(summary["total_budget"]))
    c2.metric("Planned expenses", _money(summary["planned_expenses"]))
    c3.metric("Remaining", _money(summary["remaining_budget"]))
    if summary["over_budget"]:
        st.warning("Your planned expenses exceed the wedding budget.")
    st.subheader("Add an expense")
    with st.form("add_expense"):
        category = st.selectbox("Category", CATEGORIES)
        description = st.text_input("Description")
        amount = st.number_input("Amount (INR)", min_value=0.0, step=1000.0)
        kind = st.selectbox("Expense type", ["planned", "confirmed", "actual"])
        if st.form_submit_button("Save expense"):
            db.add(Expense(wedding_id=wedding.id, category=category, description=description,
                           amount=amount, expense_type=kind))
            db.commit()
            st.success("Expense saved.")
            st.rerun()
    expenses = db.scalars(select(Expense).where(Expense.wedding_id == wedding.id)).all()
    if expenses:
        st.dataframe([{"Category": x.category, "Description": x.description,
                       "Amount": _money(x.amount), "Type": x.expense_type} for x in expenses],
                     width="stretch", hide_index=True)


def _checklist_tab(db, wedding):
    with st.form("add_task"):
        title = st.text_input("Task")
        due = st.date_input("Due date", value=date.today())
        priority = st.selectbox("Priority", ["low", "medium", "high"])
        if st.form_submit_button("Add task") and title.strip():
            db.add(WeddingTask(wedding_id=wedding.id, title=title.strip(),
                               due_date=due, priority=priority))
            db.commit()
            st.rerun()
    tasks = db.scalars(select(WeddingTask).where(WeddingTask.wedding_id == wedding.id)
                       .order_by(WeddingTask.due_date)).all()
    for task in tasks:
        col1, col2 = st.columns([4, 1])
        col1.write(f"**{task.title}** · {task.due_date or 'No due date'} · {task.priority}")
        if task.status != "completed" and col2.button("Complete", key=f"task_{task.id}"):
            task.status = "completed"
            db.commit()
            st.rerun()
        elif task.status == "completed":
            col2.success("Done")


def _profile_tab(db, wedding):
    with st.form("profile"):
        c1, c2 = st.columns(2)
        bride = c1.text_input("Bride", wedding.bride_name)
        groom = c2.text_input("Groom", wedding.groom_name)
        city = c1.text_input("City", wedding.city)
        state = c2.text_input("State", wedding.state)
        guests = st.number_input("Guests", min_value=1, max_value=100000, value=int(wedding.guest_count))
        budget = st.number_input("Budget (INR)", min_value=0.0, value=float(wedding.total_budget))
        style = st.selectbox("Style", ["Traditional", "Modern", "Classic", "Minimal", "Luxury", "Fusion"],
                             index=["Traditional", "Modern", "Classic", "Minimal", "Luxury", "Fusion"].index(
                                 wedding.wedding_style if wedding.wedding_style in
                                 ["Traditional", "Modern", "Classic", "Minimal", "Luxury", "Fusion"] else "Traditional"))
        if st.form_submit_button("Save wedding profile"):
            wedding.bride_name, wedding.groom_name = bride, groom
            wedding.city, wedding.state = city, state
            wedding.guest_count, wedding.total_budget = int(guests), budget
            wedding.wedding_style = style
            db.commit()
            st.success("Wedding profile updated.")


def _pdf_tab(db, wedding, user_id):
    st.subheader("Your wedding plan document")
    st.write("A new version is generated from the wedding profile, saved choices, recorded quotations, expenses and checklist.")
    selected = db.scalars(select(Vendor).where(
        Vendor.wedding_id == wedding.id,
        Vendor.selection_status.in_(["selected", "quotation_received", "booked"]),
    )).all()
    st.metric("Confirmed selections included", len(selected))
    if st.button("Generate latest wedding PDF", type="primary"):
        try:
            path, version = generate_wedding_pdf(db, wedding.id, user_id)
            st.session_state.latest_pdf = str(path)
            st.session_state.latest_version = version
            st.success(f"Generated PDF version {version}.")
        except Exception as exc:
            st.error(str(exc))
    path_value = st.session_state.get("latest_pdf")
    if path_value and Path(path_value).exists():
        path = Path(path_value)
        st.download_button("Download wedding plan PDF", path.read_bytes(),
                           file_name=path.name, mime="application/pdf")
    st.divider()
    st.subheader("Email the latest PDF")
    try:
        recipients = allowed_recipients(db, wedding.id, user_id)
        if recipients:
            label = st.selectbox("Recipient", list(recipients))
            confirmed = st.checkbox("I confirm that this PDF should be emailed to this recipient.")
            if st.button("Generate and send PDF", disabled=not confirmed):
                path, version = generate_wedding_pdf(db, wedding.id, user_id)
                send_wedding_pdf(db, wedding_id=wedding.id, user_id=user_id,
                                 recipient=recipients[label], pdf_path=path, pdf_version=version)
                st.success(f"PDF version {version} sent.")
        else:
            st.info("No authorised email recipients are available.")
    except Exception as exc:
        st.error(str(exc))


def app():
    user_id = st.session_state.user_id
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if not user:
            st.session_state.clear()
            st.rerun()
        st.markdown("""
        <style>
        /* High-contrast EverAfter theme: readable labels, inputs and date picker */
        :root {
            --ea-bg: #fffaf5;
            --ea-panel: #ffffff;
            --ea-text: #241815;
            --ea-muted: #594742;
            --ea-accent: #71343b;
            --ea-accent-hover: #54252b;
            --ea-border: #9a8178;
        }
        .stApp, [data-testid="stAppViewContainer"] {
            background: var(--ea-bg) !important;
            color: var(--ea-text) !important;
        }
        [data-testid="stHeader"] { background: var(--ea-bg) !important; }
        [data-testid="stSidebar"] {
            background: #f0e2d8 !important;
            border-right: 1px solid #c8b2a6;
        }
        [data-testid="stSidebar"] * { color: var(--ea-text) !important; }
        h1, h2, h3, h4, p, label, .stMarkdown, [data-testid="stCaptionContainer"] {
            color: var(--ea-text) !important;
        }
        [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] label,
        .stRadio label, .stCheckbox label {
            color: #241815 !important;
            font-weight: 600 !important;
        }
        input, textarea,
        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea,
        [data-baseweb="select"] > div {
            background: #ffffff !important;
            color: #211714 !important;
            -webkit-text-fill-color: #211714 !important;
            border: 1px solid var(--ea-border) !important;
            border-radius: 8px !important;
        }
        input::placeholder, textarea::placeholder {
            color: #6a5952 !important;
            -webkit-text-fill-color: #6a5952 !important;
            opacity: 1 !important;
        }
        [data-testid="stDateInput"] input {
            background: #ffffff !important;
            color: #211714 !important;
            -webkit-text-fill-color: #211714 !important;
        }
        [data-testid="stDateInput"] button,
        [data-testid="stDateInput"] svg {
            color: #211714 !important;
            fill: #211714 !important;
        }
        [data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] {
            background: #fffdfb !important;
            border: 1px solid #d1bdb2 !important;
            border-radius: 12px !important;
        }
        .stButton > button, [data-testid="stFormSubmitButton"] button {
            background: var(--ea-accent) !important;
            color: #ffffff !important;
            border: 1px solid var(--ea-accent) !important;
            border-radius: 9px !important;
            font-weight: 700 !important;
        }
        .stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover {
            background: var(--ea-accent-hover) !important;
            color: #ffffff !important;
        }
        [data-testid="stMetric"] {
            background: #f2e3dc !important;
            border: 1px solid #cdb5aa !important;
            padding: 14px;
            border-radius: 12px;
        }
        [data-testid="stMetric"] label,
        [data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #241815 !important;
        }
        [data-testid="stAlert"] * { color: #241815 !important; }
        </style>
        """, unsafe_allow_html=True)
        if st.sidebar.button("Log out"):
            st.session_state.clear()
            st.rerun()
        st.sidebar.write(f"Signed in as {user.full_name}")
        projects = db.scalars(select(Wedding).join(WeddingMember)
                              .where(WeddingMember.user_id == user_id)).all()
        if not projects:
            _create_project(db, user)
            return
        wedding = st.selectbox("Wedding workspace", projects,
            format_func=lambda x: f"{x.bride_name} & {x.groom_name} · {x.city}")
        st.title(f"{wedding.bride_name} & {wedding.groom_name}")
        st.caption(f"{wedding.wedding_date or 'Date to be confirmed'} · {wedding.city}, {wedding.state} · {wedding.guest_count} guests")
        tabs = st.tabs(["Overview", "Find providers", "My choices", "Budget", "Checklist", "Wedding profile", "PDF & email"])
        with tabs[0]:
            summary = budget_summary(db, wedding.id, user_id)
            a, b, c = st.columns(3)
            a.metric("Wedding budget", _money(summary["total_budget"]))
            b.metric("Planned spend", _money(summary["planned_expenses"]))
            c.metric("Budget remaining", _money(summary["remaining_budget"]))
            chosen = db.scalars(select(Vendor).where(
                Vendor.wedding_id == wedding.id,
                Vendor.selection_status.in_(["selected", "quotation_received", "booked"]),
            )).all()
            st.metric("Services selected / booked", len(chosen))
            st.info("Start in ‘Find providers’: search one service category, inspect sources and details, then shortlist or select providers. Your choices are saved to this wedding.")
        with tabs[1]:
            _research_tab(db, wedding)
        with tabs[2]:
            _my_choices_tab(db, wedding)
        with tabs[3]:
            _budget_tab(db, wedding, user_id)
        with tabs[4]:
            _checklist_tab(db, wedding)
        with tabs[5]:
            _profile_tab(db, wedding)
        with tabs[6]:
            _pdf_tab(db, wedding, user_id)
