"""Tests for temporal activities generation module."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import json

from app.temporal.activities.generation import (
    generate_readme_activity,
    generate_deep_readme_activity,
    analyze_codebase_activity,
    generate_doc_activity,
)


class TestGenerationActivities:
    """Test suite for generation activities module."""

    @pytest.mark.asyncio
    @patch('app.temporal.activities.generation.llm_service.generate_readme')
    async def test_generate_readme_activity_happy_path(self, mock_generate):
        """Test README generation with valid inputs."""
        mock_generate.return_value = "# MyRepo\n\nA great repo."
        
        result = await generate_readme_activity(
            "my-repo",
            ["src/", "tests/", "README.md"],
            "A Python package for data processing"
        )
        
        assert "MyRepo" in result
        assert "A great repo" in result
        mock_generate.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.temporal.activities.generation.llm_service.generate_readme')
    async def test_generate_readme_activity_empty_structure(self, mock_generate):
        """Test README generation with empty file structure."""
        mock_generate.return_value = "# MyRepo\n\nEmpty project."
        
        result = await generate_readme_activity(
            "empty-repo",
            [],
            "An empty project"
        )
        
        assert result is not None
        mock_generate.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.temporal.activities.generation.llm_service.generate_readme')
    async def test_generate_readme_activity_llm_error(self, mock_generate):
        """Test README generation when LLM service fails."""
        mock_generate.side_effect = Exception("LLM service unavailable")
        
        with pytest.raises(Exception) as exc_info:
            await generate_readme_activity(
                "broken-repo",
                ["src/"],
                "A broken repo"
            )
        
        assert "LLM service unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('app.temporal.activities.generation.llm_service.generate_deep_readme')
    async def test_generate_deep_readme_activity_happy_path(self, mock_generate):
        """Test deep README generation with valid inputs."""
        mock_generate.return_value = "# MyRepo\n\n## Architecture\nComplex."
        
        result = await generate_deep_readme_activity(
            "complex-repo",
            "A complex Python package",
            [{"name": "src", "type": "directory"}],
            {"requirements.txt": "fastapi==0.100.0"}
        )
        
        assert "Architecture" in result
        mock_generate.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.temporal.activities.generation.llm_service.generate_deep_readme')
    async def test_generate_deep_readme_activity_missing_tech_stack(self, mock_generate):
        """Test deep README generation with missing tech stack files."""
        mock_generate.return_value = "# MyRepo\n\nMinimal."
        
        result = await generate_deep_readme_activity(
            "minimal-repo",
            "A minimal repo",
            [],
            {}
        )
        
        assert "MyRepo" in result
        mock_generate.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.temporal.activities.generation.llm_service.analyze_codebase')
    async def test_analyze_codebase_activity_happy_path(self, mock_analyze):
        """Test codebase analysis with valid inputs."""
        analysis = {"patterns": ["async", "fastapi"], "complexity": "high"}
        mock_analyze.return_value = json.dumps(analysis)
        
        result = await analyze_codebase_activity(
            "complex-repo",
            "A complex API",
            [{"name": "app.py", "type": "file"}],
            {"setup.py": "setuptools"}
        )
        
        data = json.loads(result)
        assert "patterns" in data
        assert data["complexity"] == "high"
        mock_analyze.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.temporal.activities.generation.llm_service.analyze_codebase')
    async def test_analyze_codebase_activity_llm_error(self, mock_analyze):
        """Test codebase analysis when LLM fails."""
        mock_analyze.side_effect = Exception("Analysis failed")
        
        with pytest.raises(Exception) as exc_info:
            await analyze_codebase_activity(
                "failing-repo",
                "A failing repo",
                [],
                {}
            )
        
        assert "Analysis failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_doc_activity_happy_path(self):
        """Test single doc generation with valid inputs."""
        with patch('app.temporal.activities.generation.llm_service.generate_doc') as mock_generate:
            with patch('app.temporal.activities.generation.llm_service.DOC_TYPE_FILENAMES', 
                      {'architecture': 'ARCHITECTURE.md'}):
                mock_generate.return_value = "# Architecture\n\nDetailed design."
                
                result = await generate_doc_activity(
                    '{"summary": "test"}',
                    'architecture',
                    'my-repo',
                    [],
                    {}
                )
                
                assert isinstance(result, dict)
                assert result["filename"] == "ARCHITECTURE.md"
                assert "Architecture" in result["content"]

    @pytest.mark.asyncio
    async def test_generate_doc_activity_generation_error(self):
        """Test doc generation when generation fails."""
        with patch('app.temporal.activities.generation.llm_service.generate_doc') as mock_generate:
            with patch('app.temporal.activities.generation.llm_service.DOC_TYPE_FILENAMES',
                      {'api': 'API.md'}):
                mock_generate.side_effect = Exception("Generation error")
                
                result = await generate_doc_activity(
                    '{"summary": "test"}',
                    'api',
                    'my-repo',
                    [],
                    {}
                )
                
                assert isinstance(result, dict)
                assert result["error"] is not None
                assert "Generation error" in result["error"]
