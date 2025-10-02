"""This module renders the streamlit app for the Cache Interact Action."""

from typing import Any, Dict, List

import streamlit as st
from jvclient.lib.utils import call_api, get_reports_payload
from jvclient.lib.widgets import app_controls, app_header, app_update_action
from streamlit_router import StreamlitRouter


def render(router: StreamlitRouter, agent_id: str, action_id: str, info: dict) -> None:
    """Render the Streamlit app for the Cache Interact Action.

    Args:
        router: The StreamlitRouter instance
        agent_id: The agent ID
        action_id: The action ID
        info: The action info dict
    """
    # Initialize session state
    if "search_results" not in st.session_state:
        st.session_state.search_results = None
    if "error_message" not in st.session_state:
        st.session_state.error_message = None

    # Add app header controls
    (model_key, module_root) = app_header(agent_id, action_id, info)

    # Configuration section
    with st.expander("⚙️ Cache Interact Action Configuration", expanded=False):
        app_controls(
            agent_id,
            action_id,
            ["can_use_filter", "total_token_saved", "functions", "anchors"],
        )
        app_update_action(agent_id, action_id)

    # Search section
    st.markdown("---")
    st.subheader(
        f"🔍 Search Cached Responses | Total tokens saved: {st.session_state[model_key]['total_token_saved']}"
    )

    # st.subheader(f"Total tokens saved: {st.session_state[model_key]["total_token_saved"]}")

    # st.markdown("---")
    # st.subheader("🔍 Search Cached Responses")

    query = st.text_input(
        "Search Query",
        placeholder="Enter your search query...",
        help="Text to search for in cached responses",
    )
    filter = st.text_input(
        "Filter",
        placeholder="Optional filter...",
        help="Additional filter criteria",
        value="metadata.document_type:==cache_response",
    )

    score_threshold = st.number_input(
        "Score Threshold", min_value=0.0, max_value=1.0, value=0.015, step=0.001
    )

    # Search button
    if st.button("🚀 Search", type="primary", use_container_width=True):
        if not query.strip():
            st.warning("Please enter a search query")
        else:
            with st.spinner("Searching cached responses..."):
                search_cached_responses(agent_id, query, filter, score_threshold)

    # Display error message if any
    if st.session_state.error_message:
        st.error(st.session_state.error_message)
        if st.button("Clear Error"):
            st.session_state.error_message = None
            st.rerun()

    # Display search results
    if st.session_state.search_results:
        display_search_results(
            st.session_state.search_results, agent_id, model_key, module_root
        )


def search_cached_responses(
    agent_id: str, query: str, filter: str, score_threshold: float
) -> None:
    """Search for cached responses and update session state."""
    json_data = {
        "query": query,
        "agent_id": agent_id,
        "filter": filter,
        "score_threshold": score_threshold,
    }

    try:
        response = call_api(
            endpoint="action/walker/cache_interact_action/get_cached_response",
            json_data=json_data,
        )

        if response and response.status_code == 200:
            result = get_reports_payload(response)
            st.session_state.search_results = result
            st.session_state.error_message = None
        else:
            st.session_state.search_results = None
            st.session_state.error_message = f"API request failed with status code: {getattr(response, 'status_code', 'Unknown')}"

    except Exception as e:
        st.session_state.search_results = None
        st.session_state.error_message = f"Error searching cached responses: {str(e)}"


def display_search_results(
    results: List[Dict[str, Any]], agent_id: str, model_key: str, module_root: str
) -> None:
    """Display search results with editing and deletion capabilities."""
    st.markdown("---")
    st.subheader(f"📊 Search Results ({len(results)} found)")

    if not results:
        st.info("No cached responses found matching your criteria.")
        return

    for idx, item in enumerate(results):
        with st.container():
            st.markdown(f"### Result #{idx + 1}")
            if not st.session_state.get(f"editing_{idx}") or not st.session_state.get(
                f"deleting_{idx}"
            ):

                # Original Query
                with st.expander("📝 Original Query", expanded=True):
                    st.write(item.get("content", "No content available"))

                # AI Response
                with st.expander("🤖 AI Response", expanded=True):
                    response_data = item.get("metadata", {}).get("response", {})
                    message_content = response_data.get("message", {}).get(
                        "content", "No response content"
                    )
                    st.write(message_content)

                # Metadata
                with st.expander("📋 Metadata", expanded=False):
                    metadata = item.get("metadata", {})

                    st.text(f"Hit Count: {metadata.get('hit_count', 0)}")
                    st.text(f"Expire Days: {metadata.get('expire_days', 0)}")
                    st.text(f"Session ID: {response_data.get('session_id', 'N/A')}")
                    st.text(f"Tokens: {response_data.get('tokens', 'N/A')}")
                    st.text(f"Message Type: {response_data.get('message_type', 'N/A')}")

                st.markdown("### Actions")

                # Edit button
                if st.button("✏️ Edit", key=f"edit_{idx}", use_container_width=True):
                    st.session_state[f"editing_{idx}"] = True

                # Delete button
                if st.button("🗑️ Delete", key=f"delete_{idx}", use_container_width=True):
                    st.session_state[f"deleting_{idx}"] = True

            # Edit mode
            if st.session_state.get(f"editing_{idx}"):
                _render_edit_mode(
                    doc=item,
                    doc_id=item.get("metadata", {}).get("response_id"),
                    agent_id=agent_id,
                    model_key=model_key,
                    module_root=module_root,
                    item_idx=idx,
                )

            # Delete confirmation
            if st.session_state.get(f"deleting_{idx}"):
                _render_delete_confirmation(
                    doc_id=item.get("metadata", {}).get("response_id"),
                    agent_id=agent_id,
                    model_key=model_key,
                    module_root=module_root,
                    item_idx=idx,
                )

            st.markdown("---")


def _render_edit_mode(
    doc: Dict[str, Any],
    doc_id: str,
    agent_id: str,
    model_key: str,
    module_root: str,
    item_idx: int,
) -> None:
    """Render the document edit UI."""
    st.warning(f"Editing document {doc_id}")

    # Initialize editable state if not exists
    edit_key = f"editable_{item_idx}"
    if edit_key not in st.session_state:
        st.session_state[edit_key] = doc.copy()

    editable_doc = st.session_state[edit_key]

    with st.form(key=f"edit_form_{doc_id}"):
        # Editable content
        content = st.text_area(
            "Query Content",
            value=editable_doc.get("content", ""),
            height=68,
            help="Edit the original query content",
        )

        # Editable response content
        st.subheader("AI Response")
        response_data = editable_doc.get("metadata", {}).get("response", {})
        message_content = st.text_area(
            "AI Response Content",
            value=response_data.get("message", {}).get("content", ""),
            height=200,
            help="Edit the AI response content",
        )

        # Metadata editing
        st.subheader("Metadata")
        metadata = editable_doc.get("metadata", {})

        hit_count = st.number_input(
            "Hit Count",
            value=int(metadata.get("hit_count", 0)),
            min_value=0,
            key=f"hit_count_{doc_id}",
        )

        expire_days = st.number_input(
            "Expire Days",
            value=int(metadata.get("expire_days", 0)),
            min_value=0,
            key=f"expire_days_{doc_id}",
        )

        # Form actions
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            save_button = st.form_submit_button("💾 Save", use_container_width=True)
        with col2:
            cancel_button = st.form_submit_button("❌ Cancel", use_container_width=True)

        if save_button:
            # Update the document structure

            # latest info
            updated_doc = {
                "id": doc_id,
                "text": content,
                "metadata": {
                    **metadata,
                    "expire_days": expire_days,
                    "hit_count": hit_count,
                    "response": {
                        **response_data,
                        "message": {
                            **response_data.get("message", {}),
                            "content": message_content,
                        },
                    },
                },
            }
            st.write(updated_doc)

            # expected format st.session_state[edit_key] =  {'id': '0911a8f4-0f40-44b9-a789-e4b88d577da1', 'metadata': {'created_on': '2025-10-02T16:55:45.515705+00:00', 'document_type': 'cache_response', 'expire_days': '1', 'hit_count': '1', 'query': 'i would like to check out IND5632', 'response': '{\'data\': {}, \'id\': \'o:InteractionResponse:68deae8231b80b171d75d857\', \'message\': {\'content\': \'Here are the details for product IND5632 that you requested.\\n\\n**"BETA STAR IND5632 MOTOR/ELECTRIC 5HP,1725RPM,220V, 60HZ BETASTAR":** The BETA STAR IND5632 is a 5HP electric motor with 1725 RPM and 220V, designed for efficient, low-maintenance operation. Ideal for industrial applications needing reliable, long-lasting performance. Properly maintained, it can run over three years without major repairs.\\n\\nPrice: **$135000** (VAT Exclusive)\\n\\n[View Details](https://www.silviesonline.com/ind5632-motor-electric-5hp1725rpm220v-60hz-betasta.html)\\n\\n![image](https://cdn.shoplightspeed.com/shops/668079/files/60546442/300x300x2/image.jpg)\\n\\nLet me know if you have any questions about this motor or need help with anything else!\\n\\n\\n\', \'data\': {\'phoneme_content\': \'Here are the details for product IND5632 that you requested. Let me know if you have any questions about this motor or need help with anything else!\'}, \'id\': \'o:TextInteractionMessage:68deae8f31b80b171d75d869\', \'message_type\': \'TEXT\', \'mime\': \'\'}, \'message_type\': \'TEXT\', \'session_id\': \'4b4525f5-0505-4576-a84e-ab904f1d8e2a\', \'tokens\': 1810}', 'response_id': '0911a8f4-0f40-44b9-a789-e4b88d577da1'}, 'text': 'i would like to check out IND5632'}

            # update this to match the expected format st.session_state[edit_key] = {"content":"Which industries does Silvies Industrial Solutions serve?","metadata":{"created_on":"2025-10-02T16:53:21.774509+00:00","document_type":"cache_response","expire_days":0,"hit_count":1,"query":"Which industries does Silvies Industrial Solutions serve?","response":{"data":{},"id":"o:InteractionResponse:68deadf531b80b171d75d817","message":{"content":"Hello! I'm Silvie, a sales associate at Silvie's Industrial Solutions. Before we continue, please take a moment to read our AI policy, which includes our privacy policy.\n\nRegarding your question, we serve a variety of industries, including manufacturing, construction, food processing, mining, agriculture, and more. What can I assist you with today?","data":{"phoneme_content":"Hello! I'm Silvie, a sales associate at Silvie's Industrial Solutions. Before we continue, please take a moment to read our AI policy, which includes our privacy policy.\n\nRegarding your question, we serve a variety of industries, including manufacturing, construction, food processing, mining, agriculture, and more. What can I assist you with today?"},"id":"o:TextInteractionMessage:68deadff31b80b171d75d828","message_type":"TEXT","mime":""},"message_type":"TEXT","session_id":"4b4525f5-0505-4576-a84e-ab904f1d8e2a","tokens":2522},"response_id":"caa97491-b3f7-479f-944c-1dcd8ec2ee79"}}

            if call_update_document(agent_id, module_root, doc_id, updated_doc):
                st.success("Document updated successfully!")
                st.session_state[f"editing_{item_idx}"] = False
                st.session_state.pop(edit_key, None)
                st.rerun()
            else:
                st.error("Failed to update document")

        if cancel_button:
            st.session_state[f"editing_{item_idx}"] = False
            st.session_state.pop(edit_key, None)
            st.rerun()


def _render_delete_confirmation(
    doc_id: str, agent_id: str, model_key: str, module_root: str, item_idx: int
) -> None:
    """Render the delete confirmation UI."""
    st.error(
        f"Are you sure you want to delete document {doc_id}? This action cannot be undone."
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "✅ Confirm Delete",
            key=f"confirm_delete_{doc_id}",
            use_container_width=True,
        ):
            if call_delete_document(agent_id, module_root, doc_id):
                st.success("Document deleted successfully!")
                st.session_state[f"deleting_{item_idx}"] = False
                # Refresh search results
                st.session_state.search_results = None
                st.rerun()
            else:
                st.error("Failed to delete document")

    with col2:
        if st.button(
            "❌ Cancel", key=f"cancel_delete_{doc_id}", use_container_width=True
        ):
            st.session_state[f"deleting_{item_idx}"] = False
            st.rerun()


def call_delete_document(agent_id: str, module_root: str, doc_id: str) -> bool:
    """Call the delete_document walker in the Typesense Vector Store Action.

    Returns:
        True if successful, False otherwise
    """
    try:
        args = {"id": doc_id, "agent_id": agent_id}
        result = call_api(
            endpoint="action/walker/typesense_vector_store_action/delete_document",
            json_data=args,
        )

        return result and result.status_code == 200
    except Exception as e:
        st.error(f"Error deleting document: {str(e)}")
        return False


def call_update_document(
    agent_id: str, module_root: str, doc_id: str, data: Dict[str, Any]
) -> bool:
    """Call the update_document walker in the Typesense Vector Store Action.

    Returns:
        True if successful, False otherwise
    """
    try:
        args = {"id": doc_id, "data": data, "agent_id": agent_id}
        result = call_api(
            endpoint="action/walker/typesense_vector_store_action/update_document",
            json_data=args,
        )

        return result and result.status_code == 200
    except Exception as e:
        st.error(f"Error updating document: {str(e)}")
        return False
