from __future__ import annotations

import streamlit as st

from ui.css import apply_css
from core.state import init_state, current_base_and_feats
from ui.sidebar import render_sidebar
from ui.tabs import render_all_tabs

def main():
    """Main function to initialize and render the NeuroNexus-ai Streamlit app.

    This function configures the Streamlit page, applies custom CSS styling,
    initializes session state, renders the sidebar UI, and loads all tabs
    based on the current base URL and features.
    """
    st.set_page_config(
        page_title="NeuroNexus-ai",
        page_icon="🚀",
        layout="wide"
    )

    apply_css()            # Applies custom styles from .streamlit/neuroserve.css
    init_state()           # Initializes the session state variables

    render_sidebar()       # Handles UI for server, token, and badge management

    base_url, feats = current_base_and_feats()  # Retrieves current base URL and features
    render_all_tabs(base_url, feats)            # Renders all tabs based on available features


if __name__ == "__main__":
    main()