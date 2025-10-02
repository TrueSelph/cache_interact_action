import traceback;
import logging;
import uuid;
import from logging { Logger }
import from typing { Optional }
import from datetime { datetime, timezone }

import from jivas.agent.action.interact_action { InteractAction }
import from jivas.agent.action.agent_graph_walker { agent_graph_walker }
import from jivas.agent.memory.interaction_response { InteractionMessage, MessageType, TextInteractionMessage, MultiInteractionMessage, MediaInteractionMessage }


node CacheInteractAction(InteractAction) {

    static has logger: Logger = logging.getLogger(__name__);

    has vector_store_action:str = "TypesenseVectorStoreAction";
    has retrieval_interact_action:str = "TypesenseRetrievalInteractAction";
    has score_threshold:float = 0.015;
    has expire_days:int = 0; # zero means no expiration
    has k:int = 1;
    has metadata:bool = True;
    has can_use_filter:bool = False;
    has total_token_saved:int = 0;

    has model_action:str = "LangChainModelAction";
    has model_name:str = "gpt-4.1";
    has model_temperature:float = 0.0;
    has model_max_tokens:int = 4096;

    has validate_prompt:str = """You are a response validator for an AI assistant. Evaluate if the provided response is appropriate and accurate given the user's query and retrieved context data.

Query:
{utterance}

Retrieved Context:
{retrieval_data}

Response:
{response}

Validation Criteria:
1. Relevance: Does the response directly address the query?
2. Accuracy: Is the information factually correct based on retrieved context?
3. Completeness: Does it fully answer the query without missing key details?
4. Consistency: Does it align with the context data provided?
5. Appropriateness: Is the response suitable for the query type?

Return a valid JSON object with status "VALID" if all criteria are met, or "INVALID: if not.
""";

    def touch(visitor: agent_graph_walker) -> bool {
        return ( visitor.utterance and visitor.interaction_node.has_response());
    }

    def execute(visitor: agent_graph_walker) -> None {
        self.add_cache_response(visitor);
    }

    def add_cache_response(visitor: agent_graph_walker, expire_days:Optional[int] = None) -> None {
        # """
        # Add a cached response to the vector store.

        # :param visitor: The current visitor.
        # :param expire_days: The number of days after which the cached response should expire. Defaults to None, meaning no expiration.
        # """

        response_cached = visitor.interaction_node.data_get("response_cached");

        if not response_cached {
            cached_result = self.get_cached_response(visitor);
            if not cached_result.get("message") {
                valid_result = self.validate_response(visitor);
                if not valid_result {
                    return;
                }
                if not expire_days {
                    expire_days = self.expire_days;
                }

                # get existing cache response and update it
                if cached_result.get("expired", False) {
                    response_id = cached_result["id"];
                } else {
                    response_id = str(uuid.uuid4());
                }

                metadatas = {
                    "query": visitor.utterance,
                    "response": visitor.interaction_node.response.export(),
                    "created_on": str((datetime.now(timezone.utc)).isoformat()),
                    "hit_count": 0,
                    "document_type": "cache_response",
                    "expire_days": expire_days,
                    "response_id": response_id
                };

                if vector_store_api := self.get_agent().get_action(self.vector_store_action) {
                    vector_store_api.add_texts(ids=[response_id], texts=[visitor.utterance], metadatas=[metadatas]);
                    self.can_use_filter = True;
                } else {
                    self.logger.error("vector_store_action not found");
                }
                visitor.interaction_node.data_set("response_cached", True);
            }
        }
    }

    def get_cached_response(visitor: agent_graph_walker, confidence:float = 0.0) -> dict {
        # """
        # Retrieve a cached response from the vector store.

        # :param visitor: The current visitor.
        # :param confidence: The confidence threshold for the cached response. Defaults to 0.0.
        # :return: A dictionary containing the cached response, or an empty dictionary if no cached response is found.
        # """

        content_filter = "metadata.document_type:==cache_response";

        context_data = self.retrieve_context(query=visitor.utterance, filter=content_filter, score_threshold=confidence);
        if not context_data {
            return {
                "expired": False,
                "message": None,
                "id": None
            };
        }

        # check if expired
        expire_days = context_data[0]["metadata"]["expire_days"];
        if expire_days != 0 {
            created_on_str = context_data[0]["metadata"]["created_on"];
            created_on = datetime.fromisoformat(created_on_str.replace('Z', '+00:00'));  # Handle 'Z' if present
            now = datetime.now(timezone.utc);
            delta = now - created_on;
            days_diff = delta.days;

            if days_diff > expire_days {
                return {
                    "expired": True,
                    "message": None,
                    "id": context_data[0]["metadata"]["response_id"]
                };
            }
        }

        # update total token saved
        self.total_token_saved = self.total_token_saved + context_data[0]["metadata"]["response"]["tokens"];
        visitor.interaction_node.data_set("response_cached", True);

        # update hit count
        if vector_store_api := self.get_agent().get_action(self.vector_store_action) {
            metadatas = context_data[0]["metadata"];
            metadatas["hit_count"] = metadatas["hit_count"] + 1;
            vector_store_api.add_texts(ids=[metadatas["response_id"]], texts=[context_data[0]["content"]], metadatas=[metadatas]);
        } else {
            self.logger.error("vector_store_action not found");
        }

        return {
            "expired": False,
            "message": self.prepare_interaction_message(message=context_data[0]["metadata"]["response"]['message']),
            "id": context_data[0]["metadata"]["response_id"]
        };
    }

    def retrieve_context(query:str, filter:Optional[str] = "metadata.document_type:==cache_response", score_threshold:float = 0.0) -> list {
        # override to implement custom retrieval operation

        # """
        # retrieves document for context

        # :param visitor (InteractGraphWalker) – interact graph walker state containing interaction, utterance, etc.

        # :returns context data relevant for RAG or [] if no context is found
        # """
        context_data = [];

        if score_threshold == 0.0 {
            score_threshold = self.score_threshold;
        }

        if(vector_store_action := self.get_agent().get_action(action_label=self.vector_store_action)) {
            if(documents_and_score := vector_store_action.similarity_search_with_score(query=query, k=self.k, filter=filter)) {
                for (doc, score) in documents_and_score {
                    if(score <= score_threshold) {
                        context_item = {
                            "content": doc.page_content
                        };
                        if(self.metadata) {
                            context_item["metadata"] = doc.metadata;
                        }
                        context_data.append(context_item);
                    }
                }
            }
        }

        return context_data;
    }

    def prepare_interaction_message(message:dict) -> InteractionMessage {
        # prepare the interaction message object based on the dict representation
        if not message {
            return None;
        }

        message_type = message.get('message_type');

        if message_type == MessageType.TEXT.value {
            interaction_message = TextInteractionMessage();
            interaction_message.load(message);
        } elif message_type == MessageType.MEDIA.value {
            interaction_message = MediaInteractionMessage();
            interaction_message.load(message);
        } elif message_type == MessageType.MULTI.value {
            interaction_message = MultiInteractionMessage();
            for message_item in message.get("content") {
                message_item_type = message_item.get("message_type");
                if message_item_type == MessageType.TEXT.value {
                    interaction_message.add_interaction_message(TextInteractionMessage(content=message_item.get("content")));
                } elif message_item_type == MessageType.MEDIA.value {
                    interaction_message.add_interaction_message(MediaInteractionMessage(mime=message_item.get("mime"), content=message_item.get("content"), data=message_item.get("data")));
                }
            }
        } else {
            return None;
        }

        return interaction_message;
    }

    def validate_response(visitor:agent_graph_walker) -> bool {
        if retrieval_interact_action := self.get_agent().get_action(action_label=self.retrieval_interact_action) {
            response_context = visitor.interaction_node.data_get(self.retrieval_interact_action, {});
            if not response_context {
                return True;
            }
        }

        prompt_messages = [{"system": self.validate_prompt}];

        model_action = self.get_agent().get_action(action_label=self.model_action);
        if not model_action {
            return False;
        }

        model_action_result = model_action.call_model(
            prompt_messages=prompt_messages,
            prompt_variables={
                "utterance": visitor.utterance,
                "retrieval_data": response_context,
                "response": visitor.interaction_node.response.export()
            },
            interaction_node=visitor.interaction_node,
            model_name=self.model_name,
            model_temperature=self.model_temperature,
            model_max_tokens=self.model_max_tokens
        );

        if not model_action_result {
            return False;
        }

        result = model_action_result.get_json_result();
        if result.get("status") == "VALID" {
            return True;
        } else {
            return False;
        }
    }

    def can_use_cache_filter() -> bool {
        return self.can_use_filter;
    }


}

