"""Tests for renderer registry functionality."""

from pathlib import Path
from cvextract.renderers import (
    CVRenderer,
    get_renderer,
    list_renderers,
    register_renderer,
)
from cvextract.renderers.renderer_registry import unregister_renderer


class TestRendererRegistry:
    """Tests for the renderer registry system."""

    def test_list_renderers_returns_built_in_renderers(self):
        """list_renderers() returns the built-in renderers."""
        renderers = list_renderers()
        
        # Should have at least 1 renderer registered
        assert len(renderers) >= 1
        
        # Extract names
        names = [r['name'] for r in renderers]
        
        # Check for built-in renderer
        assert 'private-internal-renderer' in names
        
        # Each should have a description
        for renderer in renderers:
            assert 'name' in renderer
            assert 'description' in renderer
            assert isinstance(renderer['name'], str)
            assert isinstance(renderer['description'], str)
            assert len(renderer['description']) > 0

    def test_get_renderer_returns_private_internal(self):
        """get_renderer() returns private-internal-renderer instance."""
        renderer = get_renderer('private-internal-renderer')
        
        assert renderer is not None
        assert isinstance(renderer, CVRenderer)

    def test_get_renderer_returns_none_for_unknown(self):
        """get_renderer() returns None for unknown renderer name."""
        renderer = get_renderer('nonexistent-renderer')
        
        assert renderer is None

    def test_get_renderer_with_kwargs(self):
        """get_renderer() passes kwargs to renderer constructor."""
        # Create a custom renderer that accepts kwargs
        class CustomRenderer(CVRenderer):
            """Custom test renderer."""
            
            def __init__(self, custom_param=None):
                self.custom_param = custom_param
            
            def render(self, work):
                work.output.parent.mkdir(parents=True, exist_ok=True)
                work.output.write_text("rendered")
                return work
        
        # Register it temporarily
        register_renderer('custom-test-renderer', CustomRenderer)
        
        try:
            renderer = get_renderer('custom-test-renderer', custom_param='test-value')
            
            assert renderer is not None
            assert hasattr(renderer, 'custom_param')
            assert renderer.custom_param == 'test-value'
        finally:
            # Clean up the custom renderer
            unregister_renderer('custom-test-renderer')

    def test_register_custom_renderer(self, tmp_path, make_render_work):
        """register_renderer() allows registering custom renderers."""
        
        class CustomRenderer(CVRenderer):
            """Custom test renderer for testing."""
            
            def render(self, work):
                work.output.parent.mkdir(parents=True, exist_ok=True)
                work.output.write_text("custom rendered content")
                return work
        
        # Register custom renderer
        register_renderer('custom-test-renderer', CustomRenderer)
        
        try:
            # Should now be in the list
            renderers = list_renderers()
            names = [r['name'] for r in renderers]
            assert 'custom-test-renderer' in names
            
            # Should be retrievable
            renderer = get_renderer('custom-test-renderer')
            assert renderer is not None
            assert isinstance(renderer, CustomRenderer)
            
            # Should work
            output = tmp_path / "output.txt"
            work = make_render_work({}, Path("/any/path"), output)
            result = renderer.render(work)
            assert result.output == output
            assert result.output.exists()
            assert result.output.read_text() == "custom rendered content"
        finally:
            # Clean up the custom renderer
            unregister_renderer('custom-test-renderer')

    def test_list_renderers_is_sorted(self):
        """list_renderers() returns renderers sorted by name."""
        renderers = list_renderers()
        names = [r['name'] for r in renderers]
        
        # Should be sorted
        assert names == sorted(names)

    def test_unregister_renderer_removes_renderer(self):
        """unregister_renderer() removes a renderer from the registry."""
        
        class TempRenderer(CVRenderer):
            """Temporary test renderer."""
            
            def render(self, work):
                return work
        
        # Register renderer
        register_renderer('temp-test-renderer', TempRenderer)
        
        # Verify it's registered
        assert get_renderer('temp-test-renderer') is not None
        
        # Unregister it
        unregister_renderer('temp-test-renderer')
        
        # Verify it's gone
        assert get_renderer('temp-test-renderer') is None

    def test_register_renderer_overwrites_existing(self):
        """Registering with the same name overwrites the previous renderer."""
        
        class FirstRenderer(CVRenderer):
            """First test renderer."""
            
            def render(self, work):
                work.output.write_text("first")
                return work
        
        class SecondRenderer(CVRenderer):
            """Second test renderer."""
            
            def render(self, work):
                work.output.write_text("second")
                return work
        
        # Register first renderer
        register_renderer('overwrite-test', FirstRenderer)
        
        try:
            renderer1 = get_renderer('overwrite-test')
            assert isinstance(renderer1, FirstRenderer)
            
            # Register second renderer with same name
            register_renderer('overwrite-test', SecondRenderer)
            
            renderer2 = get_renderer('overwrite-test')
            assert isinstance(renderer2, SecondRenderer)
            assert not isinstance(renderer2, FirstRenderer)
        finally:
            # Clean up
            unregister_renderer('overwrite-test')
