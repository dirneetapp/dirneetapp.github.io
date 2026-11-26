"""
Standalone script to regenerate all HTML files from menu.json
without launching the full Tkinter editor or GUI.
"""
import sys
import os
import json

# Ensure we can import editor_carta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import editor_carta as ec

class HeadlessMenuApp:
    def __init__(self):
        # Load the menu data directly
        menu_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'menu.json')
        with open(menu_path, 'r', encoding='utf-8') as f:
            self.menu_data = json.load(f)

    def get_banner_html(self):
        return ec.MenuApp.get_banner_html(self)

    def get_cart_html(self):
        return ec.MenuApp.get_cart_html(self)

    def get_lang_switcher_html(self):
        return ec.MenuApp.get_lang_switcher_html(self)

    def render_item(self, item):
        return ec.MenuApp.render_item(self, item)

    def regenerate_html(self):
        return ec.MenuApp.regenerate_html(self)

    def update_index_html(self, categories):
        return ec.MenuApp.update_index_html(self, categories)

    def generate_category_html(self, cat, categories):
        return ec.MenuApp.generate_category_html(self, cat, categories)

if __name__ == "__main__":
    print("Initializing Headless HTML Generator...")
    app = HeadlessMenuApp()
    print("Regenerating HTML files (index.html and categories)...")
    app.regenerate_html()
    print("Success! All HTML files regenerated successfully.")
