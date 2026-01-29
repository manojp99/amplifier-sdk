"""Tests for agents API endpoints."""

from fastapi.testclient import TestClient


class TestAgentsEndpoints:
    """Tests for /agents endpoints."""

    def test_create_agent(self, client: TestClient) -> None:
        """Can create an agent with valid config."""
        response = client.post(
            "/agents",
            json={
                "instructions": "You are helpful.",
                "provider": "anthropic",
                "tools": ["bash"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "agent_id" in data
        assert data["agent_id"].startswith("ag_")
        assert data["status"] == "ready"

    def test_create_agent_minimal(self, client: TestClient) -> None:
        """Can create agent with minimal config."""
        response = client.post(
            "/agents",
            json={
                "instructions": "Be helpful.",
                "provider": "anthropic",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "agent_id" in data

    def test_create_agent_missing_provider(self, client: TestClient) -> None:
        """Creating agent without provider fails."""
        response = client.post(
            "/agents",
            json={"instructions": "Be helpful."},
        )
        assert response.status_code == 422  # Validation error

    def test_list_agents_empty(self, client: TestClient) -> None:
        """List agents returns empty list initially."""
        response = client.get("/agents")
        assert response.status_code == 200
        data = response.json()
        assert data["agents"] == []
        assert data["count"] == 0

    def test_list_agents_after_create(self, client: TestClient) -> None:
        """List agents includes created agents."""
        # Create an agent
        create_response = client.post(
            "/agents",
            json={"instructions": "Test", "provider": "anthropic"},
        )
        agent_id = create_response.json()["agent_id"]

        # List should include it
        response = client.get("/agents")
        assert response.status_code == 200
        data = response.json()
        assert agent_id in data["agents"]
        assert data["count"] == 1

    def test_get_agent(self, client: TestClient) -> None:
        """Can get agent by ID."""
        # Create an agent
        create_response = client.post(
            "/agents",
            json={
                "instructions": "Test instructions",
                "provider": "anthropic",
                "tools": ["bash"],
            },
        )
        agent_id = create_response.json()["agent_id"]

        # Get it
        response = client.get(f"/agents/{agent_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == agent_id
        assert data["instructions"] == "Test instructions"
        assert data["provider"] == "anthropic"
        assert "bash" in data["tools"]

    def test_get_agent_not_found(self, client: TestClient) -> None:
        """Getting non-existent agent returns 404."""
        response = client.get("/agents/ag_nonexistent123")
        assert response.status_code == 404

    def test_delete_agent(self, client: TestClient) -> None:
        """Can delete an agent."""
        # Create an agent
        create_response = client.post(
            "/agents",
            json={"instructions": "Test", "provider": "anthropic"},
        )
        agent_id = create_response.json()["agent_id"]

        # Delete it
        response = client.delete(f"/agents/{agent_id}")
        assert response.status_code == 200
        assert response.json()["deleted"] is True

        # Verify it's gone
        get_response = client.get(f"/agents/{agent_id}")
        assert get_response.status_code == 404

    def test_delete_agent_not_found(self, client: TestClient) -> None:
        """Deleting non-existent agent returns 404."""
        response = client.delete("/agents/ag_nonexistent123")
        assert response.status_code == 404


class TestAgentRunEndpoint:
    """Tests for /agents/{id}/run endpoint."""

    def test_run_agent(self, client: TestClient) -> None:
        """Can run a prompt on an agent."""
        # Create an agent
        create_response = client.post(
            "/agents",
            json={"instructions": "Be helpful.", "provider": "anthropic"},
        )
        agent_id = create_response.json()["agent_id"]

        # Run a prompt
        response = client.post(
            f"/agents/{agent_id}/run",
            json={"prompt": "Hello!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "usage" in data
        assert "turn_count" in data

    def test_run_agent_not_found(self, client: TestClient) -> None:
        """Running prompt on non-existent agent returns 404."""
        response = client.post(
            "/agents/ag_nonexistent123/run",
            json={"prompt": "Hello!"},
        )
        assert response.status_code == 404


class TestAgentMessagesEndpoint:
    """Tests for /agents/{id}/messages endpoint."""

    def test_get_messages_empty(self, client: TestClient) -> None:
        """New agent has no messages."""
        # Create an agent
        create_response = client.post(
            "/agents",
            json={"instructions": "Be helpful.", "provider": "anthropic"},
        )
        agent_id = create_response.json()["agent_id"]

        # Get messages
        response = client.get(f"/agents/{agent_id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data

    def test_clear_messages(self, client: TestClient) -> None:
        """Can clear agent messages."""
        # Create an agent
        create_response = client.post(
            "/agents",
            json={"instructions": "Be helpful.", "provider": "anthropic"},
        )
        agent_id = create_response.json()["agent_id"]

        # Run a prompt to add messages
        client.post(f"/agents/{agent_id}/run", json={"prompt": "Hello!"})

        # Clear messages
        response = client.delete(f"/agents/{agent_id}/messages")
        assert response.status_code == 200
        assert response.json()["cleared"] is True


class TestModulesEndpoint:
    """Tests for /modules endpoint."""

    def test_list_modules(self, client: TestClient) -> None:
        """Can list available modules."""
        response = client.get("/modules")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "tools" in data
        assert "orchestrators" in data
        assert "context_managers" in data
        assert "hooks" in data
        # Check some expected modules
        assert "anthropic" in data["providers"]
        assert "bash" in data["tools"]


class TestOneOffRunEndpoint:
    """Tests for /run endpoint (one-off execution)."""

    def test_run_once(self, client: TestClient) -> None:
        """Can run a one-off prompt."""
        response = client.post(
            "/run",
            json={
                "prompt": "Hello!",
                "instructions": "Be brief.",
                "provider": "anthropic",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "usage" in data
