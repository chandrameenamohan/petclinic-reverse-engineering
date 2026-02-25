"""Tests for the base Jinja2 template — CDN links, navbar, footer."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "api_gateway" / "templates"


def _render_base() -> str:
    """Render base.html with a dummy content block."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    # Create a child template that extends base and fills the content block
    child = env.from_string('{% extends "base.html" %}{% block content %}<p id="test-content">Hello</p>{% endblock %}')
    return child.render(request=None)


class TestBaseTemplateCDN:
    """Verify CDN links are present in the base template."""

    def test_bootstrap_css(self) -> None:
        html = _render_base()
        assert "bootstrap" in html.lower()
        assert 'rel="stylesheet"' in html

    def test_bootstrap_js(self) -> None:
        html = _render_base()
        assert "bootstrap.bundle.min.js" in html or "bootstrap.min.js" in html

    def test_htmx(self) -> None:
        html = _render_base()
        assert "htmx" in html.lower()

    def test_font_awesome(self) -> None:
        html = _render_base()
        assert "font-awesome" in html.lower() or "fontawesome" in html.lower()


class TestBaseTemplateNavbar:
    """Verify navbar links."""

    def test_navbar_home_link(self) -> None:
        html = _render_base()
        assert "fa-home" in html
        assert "Home" in html

    def test_navbar_find_owners_link(self) -> None:
        html = _render_base()
        assert "fa-search" in html
        assert "Find owners" in html

    def test_navbar_register_owner_link(self) -> None:
        html = _render_base()
        assert "fa-plus" in html
        # "Register owner" or similar text
        assert "Register" in html

    def test_navbar_vets_link(self) -> None:
        html = _render_base()
        assert "fa-th-list" in html
        assert "Veterinarians" in html

    def test_navbar_has_four_links(self) -> None:
        html = _render_base()
        # Count nav-link occurrences (Bootstrap navbar pattern)
        assert html.count("nav-link") >= 4


class TestBaseTemplateStructure:
    """Verify overall structure."""

    def test_has_content_block(self) -> None:
        html = _render_base()
        assert "test-content" in html

    def test_has_footer(self) -> None:
        html = _render_base()
        assert "<footer" in html.lower()

    def test_has_html_doctype(self) -> None:
        html = _render_base()
        assert "<!DOCTYPE" in html or "<!doctype" in html

    def test_has_lang_attribute(self) -> None:
        html = _render_base()
        assert 'lang="en"' in html

    def test_custom_css_linked(self) -> None:
        html = _render_base()
        assert "petclinic.css" in html
