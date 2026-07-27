import json
from unittest.mock import MagicMock, patch

import pytest

from aws.orchestrator_lambda.content_generator import ContentGenerator
from aws.shared.exceptions import ContentGenerationError


class TestContentGenerator:
    @patch("aws.orchestrator_lambda.content_generator.boto3.client")
    def test_generate_returns_parsed_content(self, mock_boto, bedrock_response):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.invoke_model.return_value = {
            "body": MagicMock(
                read=MagicMock(
                    return_value=json.dumps(
                        {"content": [{"text": json.dumps(bedrock_response)}]}
                    ).encode()
                )
            )
        }
        generator = ContentGenerator(model_id="test-model", region="us-east-1")
        result = generator.generate(["Leadership Topic"])
        assert result["title"] == "Leading Through Change"
        assert "hashtags" in result

    @patch("aws.orchestrator_lambda.content_generator.boto3.client")
    def test_generate_missing_field_raises_error(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        incomplete = {"title": "Only Title"}
        mock_client.invoke_model.return_value = {
            "body": MagicMock(
                read=MagicMock(
                    return_value=json.dumps(
                        {"content": [{"text": json.dumps(incomplete)}]}
                    ).encode()
                )
            )
        }
        generator = ContentGenerator(model_id="test-model", region="us-east-1")
        with pytest.raises(ContentGenerationError, match="Missing required"):
            generator.generate(["Topic"])

    @patch("aws.orchestrator_lambda.content_generator.boto3.client")
    def test_generate_bedrock_api_error(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.invoke_model.side_effect = Exception("Bedrock throttled")
        generator = ContentGenerator(model_id="test-model", region="us-east-1")
        with pytest.raises(ContentGenerationError, match="Bedrock throttled"):
            generator.generate(["Topic"])

    @patch("aws.orchestrator_lambda.content_generator.boto3.client")
    def test_generate_invalid_json_response(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        mock_client.invoke_model.return_value = {
            "body": MagicMock(
                read=MagicMock(
                    return_value=json.dumps(
                        {"content": [{"text": "not valid json"}]}
                    ).encode()
                )
            )
        }
        generator = ContentGenerator(model_id="test-model", region="us-east-1")
        with pytest.raises(ContentGenerationError, match="Failed to parse"):
            generator.generate(["Topic"])

    def test_build_prompt_contains_topics(self):
        generator = ContentGenerator(model_id="test-model", region="us-east-1")
        prompt = generator._build_prompt(["Topic A", "Topic B"])
        assert "Topic A" in prompt
        assert "Topic B" in prompt

    def test_build_prompt_empty_topics(self):
        generator = ContentGenerator(model_id="test-model", region="us-east-1")
        prompt = generator._build_prompt([])
        assert "leadership development" in prompt
