"""Fortuna — Settings page for AI provider configuration."""

import streamlit as st
import database as db
import ai_engine as ai

PROVIDER_INFO = {
    "claude": {"label": "Claude (Anthropic)", "default_model": "claude-sonnet-4-6"},
    "openai": {"label": "ChatGPT (OpenAI)", "default_model": "gpt-4o"},
    "gemini": {"label": "Gemini (Google)", "default_model": "gemini-2.0-flash"},
}


def render():
    st.markdown("# Settings")
    st.markdown("## AI Providers")
    st.markdown("Configure one or more AI providers for automated analysis.")

    saved_providers = {p["provider"]: p for p in db.get_ai_providers()}

    for provider_key, info in PROVIDER_INFO.items():
        saved = saved_providers.get(provider_key)
        is_configured = bool(saved and saved["is_enabled"])

        if is_configured:
            status_html = '<span style="color: #00C853; font-weight: 600;">Configured</span>'
        else:
            status_html = '<span style="color: #FF5252; font-weight: 600;">Not configured</span>'

        st.markdown("---")
        st.markdown(
            f"### {info['label']} — {status_html}",
            unsafe_allow_html=True,
        )
        _render_provider_form(provider_key, info, saved)


def _render_provider_form(provider_key: str, info: dict, saved: dict | None):
    """Render the configuration form for a single provider."""
    prefix = f"settings_{provider_key}"

    # Row 1: API Key (full width)
    api_key = st.text_input(
        "API Key",
        value=saved["api_key"] if saved else "",
        type="password",
        key=f"{prefix}_key",
    )

    # Row 2: Model selection — [Model dropdown/input (3)] [Fetch Models button (1)]
    models_key = f"{prefix}_models"
    available_models = st.session_state.get(models_key, [])
    valid_models = [m for m in available_models if not m.startswith("Error:")]
    if available_models and not valid_models:
        st.error(available_models[0])

    col_model, col_fetch = st.columns([3, 1])

    with col_model:
        if valid_models:
            current = saved["model"] if saved and saved["model"] in valid_models else info["default_model"]
            idx = valid_models.index(current) if current in valid_models else 0
            model = st.selectbox("Model", options=valid_models, index=idx, key=f"{prefix}_model_select")
        else:
            model = st.text_input(
                "Model",
                value=saved["model"] if saved else "",
                disabled=True,
                placeholder="Click 'Fetch Models' to load available models",
                key=f"{prefix}_model_input",
            )

    with col_fetch:
        # Use a label to vertically align with the Model input
        st.markdown("<div style='height: 1.65rem;'></div>", unsafe_allow_html=True)
        if st.button("Fetch Models", key=f"{prefix}_fetch", use_container_width=True):
            if not api_key:
                st.warning("Enter an API key first.")
            else:
                with st.spinner("Fetching..."):
                    models = ai.list_models(provider_key, api_key)
                st.session_state[models_key] = models
                valid = [m for m in models if not m.startswith("Error:")]
                if valid:
                    db.update_ai_provider_models_cache(provider_key, valid)

    # Row 3: [Enabled checkbox] [Save] [Test Connection] [Delete] — all on one line
    has_delete = saved is not None
    if has_delete:
        col_enabled, col_save, col_test, col_delete = st.columns([1.5, 1, 1.5, 1])
    else:
        col_enabled, col_save, col_test = st.columns([2, 1, 1.5])
        col_delete = None

    with col_enabled:
        is_enabled = st.checkbox(
            "Enabled",
            value=saved["is_enabled"] if saved else True,
            key=f"{prefix}_enabled",
        )

    with col_save:
        st.markdown("<div style='height: 0.3rem;'></div>", unsafe_allow_html=True)
        if st.button("Save", key=f"{prefix}_save", use_container_width=True):
            if not api_key:
                st.warning("API key is required.")
            elif not model:
                st.warning("Fetch models and select one first.")
            else:
                db.upsert_ai_provider(provider_key, api_key, model, is_enabled)
                st.success("Saved.")
                st.rerun()

    with col_test:
        st.markdown("<div style='height: 0.3rem;'></div>", unsafe_allow_html=True)
        if st.button("Test Connection", key=f"{prefix}_test", use_container_width=True):
            if not api_key:
                st.warning("Enter an API key first.")
            elif not model:
                st.warning("Fetch models and select one first.")
            else:
                with st.spinner("Testing..."):
                    ok, msg = ai.test_connection(provider_key, api_key, model)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    if col_delete:
        with col_delete:
            st.markdown("<div style='height: 0.3rem;'></div>", unsafe_allow_html=True)
            if st.button("Delete", key=f"{prefix}_delete", use_container_width=True):
                db.delete_ai_provider(provider_key)
                st.session_state.pop(models_key, None)
                st.success("Deleted.")
                st.rerun()
