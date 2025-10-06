# Cache Interact Action

![GitHub release (latest by date)](https://img.shields.io/github/v/release/TrueSelph/cache_interact_action)
![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/TrueSelph/cache_interact_action/test-action.yaml)
![GitHub issues](https://img.shields.io/github/issues/TrueSelph/cache_interact_action)
![GitHub pull requests](https://img.shields.io/github/issues-pr/TrueSelph/cache_interact_action)
![GitHub](https://img.shields.io/github/license/TrueSelph/cache_interact_action)

A JIVAS action that implements intelligent response caching to reduce token usage and improve response times. The Cache Interact Action stores and retrieves AI responses from a vector database, automatically validating response quality and tracking token savings. It integrates with Typesense vector stores and includes a web interface for managing cached responses with editing and deletion capabilities.

## Package Information

- **Name:** `jivas/cache_interact_action`
- **Author:** [V75 Inc.](https://v75inc.com/)
- **Archetype:** `CacheInteractAction`
- **Version:** `0.1.0`

## Meta Information

- **Title:** Cache Interact Action
- **Description:** Reduces token usage by caching and reusing AI responses with validation and management capabilities
- **Group:** custom
- **Type:** interact_action

## Configuration

- **Singleton:** true
- **Order:**
  - **Weight:** 1
  - **After:** `jivas/persona_interact_action`

## Dependencies

- **Jivas:** `~2.1.0`
- **Actions:**
  - `jivas/persona_interact_action`: `~0.1.0`
  - `jivas/typesense_vector_store_action`: `~0.1.0`

---

## How to Use

### 1. Retrieve a Cached Response
Fetch a cached response and set it as the current message (skipping the normal retrieval action if available):

```python
if cache_retrieval_interact_action := self.get_agent().get_action(action_label="CacheInteractAction"):
    cached_result = cache_retrieval_interact_action.get_cached_response(visitor)
    if cached_result.get("message"):
        visitor.interaction_node.set_message(cached_result["message"])
        visitor.dequeue_action(action_label=self.retrieval_interact_action)
        return
```

---

### 2. Add a Response to the Cache
Cache a response from another action (with an optional expiration in days):

```python
if cache_retrieval_interact_action := self.get_agent().get_action(action_label="CacheInteractAction"):
    cache_retrieval_interact_action.add_cache_response(visitor, expire_days=1)
```

---

### Overview

The Cache Interact Action provides intelligent response caching with the following key features:

- **Automatic Response Caching**: Stores AI responses with their queries for future retrieval
- **Similarity-Based Retrieval**: Uses vector similarity search to find relevant cached responses
- **Response Validation**: Validates cached responses for quality and relevance using AI
- **Token Tracking**: Monitors and reports total tokens saved through caching
- **Expiration Management**: Supports configurable cache expiration (0 = never expires)
- **Web Interface**: Provides a Streamlit-based UI for managing cached responses

### Core Features

- **Response Quality Validation**: Uses GPT models to validate cached responses before reuse
- **Hit Count Tracking**: Tracks how often each cached response is retrieved
- **Metadata Management**: Stores comprehensive metadata including creation time, query, and response details
- **Configurable Similarity Thresholds**: Adjustable score thresholds for cache retrieval
- **Filter Support**: Advanced filtering capabilities for targeted cache searches

### Configuration Options

The action supports extensive configuration through the following parameters:

- `vector_store_action`: Vector store action label (default: "TypesenseVectorStoreAction")
- `retrieval_interact_action`: Action label for response validation (default: "CacheInteractAction")
- `score_threshold`: Similarity threshold for cache retrieval (default: 0.015)
- `expire_days`: Days until cache entries expire (default: 0, never expires)
- `k`: Number of similar results to retrieve (default: 1)
- `metadata`: Include metadata in responses (default: True)
- `can_use_filter`: Enable filter usage (default: False)
- `model_action`: Model action for validation (default: "LangChainModelAction")
- `model_name`: Model for validation (default: "gpt-4.1")
- `model_temperature`: Validation temperature (default: 0.0)
- `model_max_tokens`: Max tokens for validation (default: 4096)

### Web Interface

The Cache Interact Action includes a comprehensive Streamlit web application for managing cached responses:

#### Features

- **Search Interface**: Query cached responses with configurable filters and similarity thresholds
- **Response Management**: View, edit, and delete cached responses through an intuitive interface
- **Metadata Display**: View detailed metadata including hit counts, expiration dates, and token usage
- **Real-time Updates**: Live token savings counter and response statistics
- **Configuration Panel**: Adjust action settings and update configurations through the UI

#### Usage

1. Access the web interface through your JIVAS agent dashboard
2. Navigate to the Cache Interact Action section
3. Use the search functionality to find cached responses
4. Edit response content or metadata as needed
5. Delete outdated or incorrect cached responses
6. Monitor token savings and cache performance

### Best Practices

- **Vector Store Configuration**: Ensure the underlying vector store action is properly configured and accessible
- **Similarity Thresholds**: Adjust `score_threshold` based on your use case - lower values return more results but may include less relevant matches
- **Expiration Strategy**: Set appropriate `expire_days` values based on how current your responses need to be
- **Validation Models**: Choose appropriate models for response validation based on accuracy vs. speed requirements
- **Testing**: Test caching behavior in a staging environment before production deployment
- **Monitoring**: Regularly monitor token savings and cache hit rates to optimize performance

### API Reference

#### Walker: `get_cached_response`

A standalone walker for retrieving cached responses with custom parameters.

**Parameters:**
- `query` (str): Search query text
- `filter` (str): Filter criteria for search (default: "metadata.document_type:==cache_response")
- `score_threshold` (float): Similarity threshold (default: 0.0)
- `reporting` (bool): Enable result reporting (default: True)

**Usage:**
```jac
walker get_cached_response {
    query = "your search query";
    filter = "metadata.document_type:==cache_response";
    score_threshold = 0.015;
    reporting = True;
}
```

#### Methods

**Core Methods:**
- `add_cache_response(visitor, expire_days)`: Cache a new response
- `get_cached_response(visitor, confidence)`: Retrieve cached response with similarity matching
- `retrieve_context(query, filter, score_threshold)`: Search vector store for similar content
- `validate_response(visitor)`: Validate response quality using AI
- `can_use_cache_filter()`: Check if filter functionality is enabled

**Utility Methods:**
- `prepare_interaction_message(message)`: Convert dict to InteractionMessage object
- `touch(visitor)`: Determine if action should execute based on visitor state

### Integration Examples

#### Basic Integration

The action integrates automatically into JIVAS agent workflows. When a user query matches a cached response above the similarity threshold, the cached response is returned instead of generating a new one.

#### Custom Configuration

```jac
node MyCustomAgent {
    has cache_action: CacheInteractAction;

    def initialize() {
        // Configure for higher precision matching
        cache_action.score_threshold = 0.025;
        cache_action.expire_days = 30;  // 30-day expiration
        cache_action.k = 3;  // Return top 3 matches
    }
}
```

#### Validation Integration

The action uses AI-powered validation to ensure cached responses remain appropriate:

```jac
// Response validation prompt (configurable)
validate_prompt = """
You are a response validator for an AI assistant. Evaluate if the provided response is appropriate and accurate...

Return a valid JSON object with status "VALID" if all criteria are met, or "INVALID" if not.
""";
```

---

## 🔰 Contributing

- **🐛 [Report Issues](https://github.com/TrueSelph/cache_interact_action/issues)**: Submit bugs found or log feature requests for the `cache_interact_action` project.
- **💡 [Submit Pull Requests](https://github.com/TrueSelph/cache_interact_action/blob/main/CONTRIBUTING.md)**: Review open PRs, and submit your own PRs.

<details closed>
<summary>Contributing Guidelines</summary>

1. **Fork the Repository**: Start by forking the project repository to your GitHub account.
2. **Clone Locally**: Clone the forked repository to your local machine using a git client.
   ```sh
   git clone https://github.com/TrueSelph/cache_interact_action
   ```
3. **Create a New Branch**: Always work on a new branch, giving it a descriptive name.
   ```sh
   git checkout -b new-feature-x
   ```
4. **Make Your Changes**: Develop and test your changes locally.
5. **Commit Your Changes**: Commit with a clear message describing your updates.
   ```sh
   git commit -m 'Implemented new feature x.'
   ```
6. **Push to GitHub**: Push the changes to your forked repository.
   ```sh
   git push origin new-feature-x
   ```
7. **Submit a Pull Request**: Create a PR against the original project repository. Clearly describe the changes and their motivations.
8. **Review**: Once your PR is reviewed and approved, it will be merged into the main branch. Congratulations on your contribution!
</details>

<details open>
<summary>Contributor Graph</summary>
<br>
<p align="left">
    <a href="https://github.com/TrueSelph/cache_interact_action/graphs/contributors">
        <img src="https://contrib.rocks/image?repo=TrueSelph/cache_interact_action" />
   </a>
</p>
</details>

## 🎗 License

This project is protected under the Apache License 2.0. See [LICENSE](../LICENSE) for more information.