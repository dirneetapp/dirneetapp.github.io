import json
import os
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import re
import webbrowser
from datetime import datetime
from PIL import Image, ImageTk
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer

# --- GLOBALS & PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MENU_FILE = os.path.join(BASE_DIR, 'menu.json')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
INDEX_FILE = os.path.join(BASE_DIR, 'index.html')
PRIZES_DELIVERED_FILE = os.path.join(BASE_DIR, 'prizes_delivered.json')

# 14 Standard Allergens + Vegano
ALLERGENS = {
    "gluten": ("ðŸŒ¾", "Gluten"),
    "crustaceos": ("ðŸ¦", "CrustÃ¡ceos"),
    "huevos": ("ðŸ¥š", "Huevos"),
    "pescado": ("ðŸŸ", "Pescado"),
    "cacahuetes": ("ðŸ¥œ", "Cacahuetes"),
    "soja": ("ðŸ«˜", "Soja"),
    "lacteos": ("ðŸ¥›", "LÃ¡cteos"),
    "frutos_cascara": ("ðŸŒ°", "Frutos de cÃ¡scara"),
    "apio": ("ðŸ¥¬", "Apio"),
    "mostaza": ("ðŸŒ­", "Mostaza"),
    "sesamo": ("ðŸ¥¯", "SÃ©samo"),
    "sulfitos": ("ðŸ·", "Sulfitos"),
    "altramuces": ("ðŸŒ¼", "Altramuces"),
    "moluscos": ("ðŸ¦‘", "Moluscos"),
    "vegano": ("ðŸŒ±", "Vegano/Vegetariano")
}

MARKETING_TAGS = {
    "tag_recomendado": ("â­", "Especialidad"),
    "tag_novedad": ("ðŸ†•", "Novedad")
}

SPICE_LEVELS = {
    0: "",
    1: "ðŸŒ¶ï¸",
    2: "ðŸŒ¶ï¸ðŸŒ¶ï¸",
    3: "ðŸŒ¶ï¸ðŸŒ¶ï¸ðŸŒ¶ï¸"
}

# Ensure assets directory exists
os.makedirs(ASSETS_DIR, exist_ok=True)

def compress_and_save_image(src_path, dest_filename_base, max_size=(800, 800), force_jpg=False):
    """Comprime la imagen, la redimensiona y la guarda. Devuelve la ruta relativa."""
    ext = ".jpg" if force_jpg else ".webp"
    format_name = "JPEG" if force_jpg else "WEBP"
    dest_name = f"{dest_filename_base}{ext}"
    dest_path = os.path.join(ASSETS_DIR, dest_name)
    try:
        img = Image.open(src_path)
        if img.mode in ("RGBA", "P"): 
            img = img.convert("RGB")
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        img.save(dest_path, format_name, quality=80)
        return f"assets/{dest_name}"
    except Exception as e:
        print(f"Error comprimiendo imagen: {e}")
        orig_ext = os.path.splitext(src_path)[1]
        dest_name_fallback = f"{dest_filename_base}{orig_ext}"
        dest_fallback = os.path.join(ASSETS_DIR, dest_name_fallback)
        shutil.copy(src_path, dest_fallback)
        return f"assets/{dest_name_fallback}"


def load_delivered_prizes():
    current_month = datetime.now().strftime("%Y-%m")
    if os.path.exists(PRIZES_DELIVERED_FILE):
        try:
            with open(PRIZES_DELIVERED_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get("month") == current_month:
                    return data.get("delivered", {})
        except Exception:
            pass
    return {}


def save_delivered_prizes(delivered):
    current_month = datetime.now().strftime("%Y-%m")
    try:
        with open(PRIZES_DELIVERED_FILE, 'w', encoding='utf-8') as f:
            json.dump({"month": current_month, "delivered": delivered}, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Error saving delivered prizes:", e)


def claim_prize_locally(prize_id):
    delivered = load_delivered_prizes()
    delivered[prize_id] = delivered.get(prize_id, 0) + 1
    save_delivered_prizes(delivered)
    return delivered


class MenuApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Administrador de Carta Digital PRO")
        self.geometry("1100x750")
        
        self.menu_data = {"categories": []}
        self.load_data()
        
        # Start local API server for roulette
        self.server_port = 5000
        self.server_thread = None
        self.httpd = None
        self.start_api_server()
        
        self.create_widgets()
        self.populate_tree_cats()
        
        # Shutdown handler
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_data(self):
        if os.path.exists(MENU_FILE):
            try:
                with open(MENU_FILE, 'r', encoding='utf-8') as f:
                    self.menu_data = json.load(f)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar menu.json:\n{e}")
        else:
            self.menu_data = {"categories": []}
            
        # Initialize roulette config if missing
        if "roulette" not in self.menu_data:
            self.menu_data["roulette"] = {
                "prizes_active": True,
                "prizes": [
                    {"id": "beer", "name": "Copa de Cerveza", "quantity": 5},
                    {"id": "soda", "name": "Refresco", "quantity": 5},
                    {"id": "coffee", "name": "CafÃ©", "quantity": 5}
                ]
            }

        # Initialize github_deploy config if missing
        if "github_deploy" not in self.menu_data:
            self.menu_data["github_deploy"] = {
                "enabled": False,
                "username": "",
                "repo": "",
                "token": "",
                "branch": "main",
                "auto_sync": False
            }

    def save_data(self):
        try:
            if hasattr(self, 'var_splash_active'):
                self.menu_data["splash_active"] = self.var_splash_active.get()
                if hasattr(self, 'var_splash_imgs'):
                    self.menu_data["splash_imgs"] = [v.get() for v in self.var_splash_imgs]
                
            if hasattr(self, 'var_md_active'):
                try: p = float(self.ent_md_price.get().replace(',', '.'))
                except: p = 0.0
                self.menu_data["menu_del_dia"] = {
                    "active": self.var_md_active.get(),
                    "price": p,
                    "primeros": self.ent_md_primeros.get().strip(),
                    "segundos": self.ent_md_segundos.get().strip(),
                    "postres": self.ent_md_postres.get().strip(),
                    "includes": self.ent_md_incluye.get().strip()
                }
            if hasattr(self, 'var_banner_active'):
                self.menu_data["banner"] = {
                    "active": self.var_banner_active.get(),
                    "text": self.ent_banner_text.get().strip(),
                    "expiration": self.ent_banner_date.get().strip()
                }
            if hasattr(self, 'var_orders_enabled'):
                self.menu_data["orders_enabled"] = self.var_orders_enabled.get()
                self.menu_data["whatsapp_number"] = self.ent_whatsapp.get().strip()
            if hasattr(self, 'var_roulette_prizes_active'):
                self.menu_data.setdefault("roulette", {})["prizes_active"] = self.var_roulette_prizes_active.get()
            if hasattr(self, 'ent_github_username'):
                self.menu_data["github_deploy"] = {
                    "enabled": self.var_github_enabled.get(),
                    "username": self.ent_github_username.get().strip(),
                    "repo": self.ent_github_repo.get().strip(),
                    "token": self.ent_github_token.get().strip(),
                    "branch": self.ent_github_branch.get().strip() or "main",
                    "auto_sync": self.var_github_auto_sync.get()
                }
            # --- BACKUP LOGIC ---
            if os.path.exists(MENU_FILE):
                backup_dir = os.path.join(BASE_DIR, "backups")
                os.makedirs(backup_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                shutil.copy(MENU_FILE, os.path.join(backup_dir, f"menu_backup_{timestamp}.json"))
            # --------------------
            
            with open(MENU_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.menu_data, f, indent=2, ensure_ascii=False)
            
            # Save menu_data.js for local/CORS-free access
            js_file = os.path.join(BASE_DIR, 'menu_data.js')
            with open(js_file, 'w', encoding='utf-8') as f:
                f.write(f"const menuData = {json.dumps(self.menu_data, ensure_ascii=False)};")
                
            self.regenerate_html()

            # Auto-sync with GitHub Pages
            if self.menu_data.get("github_deploy", {}).get("auto_sync", False):
                threading.Thread(target=self.run_git_deploy_worker, args=(True,), daemon=True).start()

            messagebox.showinfo("Ã‰xito", "MenÃº guardado y sitio web actualizado correctamente.")
        except Exception as e:
            import traceback
            messagebox.showerror("Error", f"No se pudo guardar:\n{traceback.format_exc()}")

    def preview_web(self):
        if os.path.exists(INDEX_FILE):
            webbrowser.open(f"file:///{INDEX_FILE}")
        else:
            messagebox.showwarning("Aviso", "Primero debes guardar para generar la web.")

    def create_widgets(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # Tab: CategorÃ­as y Productos
        self.tab_menu = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_menu, text="CategorÃ­as y Productos")
        self.build_menu_tab()

        # Tab: Banner
        self.tab_banner = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_banner, text="Banner Promocional")
        self.build_banner_tab()

        # Tab: ImÃ¡genes Splash
        self.tab_splash = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_splash, text="ImÃ¡genes de Inicio (Splash)")
        self.build_splash_tab()
        
        # Tab: MenÃº del DÃ­a
        self.tab_menu_dia = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_menu_dia, text="MenÃº del DÃ­a")
        self.build_menu_dia_tab()
        
        # Tab: Pedidos WhatsApp
        self.tab_orders = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_orders, text="Pedidos WhatsApp")
        self.build_orders_tab()
        
        # Tab: Control de Ruleta
        self.tab_roulette = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_roulette, text="Control de Ruleta")
        self.build_roulette_tab()
        
        # Tab: Gestor de Backups
        self.tab_backups = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_backups, text="Gestor de Backups")
        self.build_backups_tab()

        # Tab: Optimizador de ImÃ¡genes
        self.tab_optimizer = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_optimizer, text="Optimizador de ImÃ¡genes")
        self.build_optimizer_tab()
        
        # Tab: QR de Mesas
        self.tab_qr = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_qr, text="QR de Mesas")
        self.build_qr_tab()

        # Tab: Nube & GitHub Pages
        self.tab_deploy = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_deploy, text="Nube & GitHub Pages")
        self.build_deploy_tab()
        
        # Save Button
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_frame, text="ðŸ’¾ Guardar y Actualizar Web", command=self.save_data, style="Accent.TButton").pack(side="right")
        ttk.Button(btn_frame, text="ðŸ‘ï¸ Vista Previa", command=self.preview_web).pack(side="right", padx=10)

    def build_menu_tab(self):
        paned = ttk.PanedWindow(self.tab_menu, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True)

        # --- LEFT: Categories & Subcategories Tree ---
        frame_cats = ttk.Frame(paned)
        paned.add(frame_cats, weight=1)
        
        ttk.Label(frame_cats, text="CategorÃ­as y SubcategorÃ­as", font=("Arial", 11, "bold")).pack(anchor="w")
        
        tree_cats_frame = ttk.Frame(frame_cats)
        tree_cats_frame.pack(fill="both", expand=True, pady=5)
        
        self.tree_cats = ttk.Treeview(tree_cats_frame, show="tree", selectmode="browse")
        self.tree_cats.pack(side="left", fill="both", expand=True)
        self.tree_cats.bind('<<TreeviewSelect>>', self.on_tree_cat_select)
        self.tree_cats.bind("<ButtonPress-1>", self.on_cat_drag_start)
        self.tree_cats.bind("<ButtonRelease-1>", self.on_cat_drag_release)
        
        # Reorder buttons for categories
        cat_order_frame = ttk.Frame(tree_cats_frame)
        cat_order_frame.pack(side="right", fill="y", padx=5)
        ttk.Button(cat_order_frame, text="â¬†", width=3, command=self.move_cat_up).pack(pady=2)
        ttk.Button(cat_order_frame, text="â¬‡", width=3, command=self.move_cat_down).pack(pady=2)

        btn_cat_frame = ttk.Frame(frame_cats)
        btn_cat_frame.pack(fill="x")
        ttk.Button(btn_cat_frame, text="âž• AÃ±adir Cat.", command=self.add_category).pack(side="left", expand=True, fill="x")
        ttk.Button(btn_cat_frame, text="âž• AÃ±adir Sub.", command=self.add_subcategory).pack(side="left", expand=True, fill="x")
        ttk.Button(btn_cat_frame, text="âœï¸ Editar", command=self.edit_category).pack(side="left", expand=True, fill="x")
        ttk.Button(btn_cat_frame, text="ðŸ—‘ï¸ Eliminar", command=self.delete_category).pack(side="left", expand=True, fill="x")

        # --- RIGHT: Items List ---
        frame_items = ttk.Frame(paned)
        paned.add(frame_items, weight=2)
        
        top_items_frame = ttk.Frame(frame_items)
        top_items_frame.pack(fill="x")
        ttk.Label(top_items_frame, text="Productos", font=("Arial", 11, "bold")).pack(side="left")
        
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.do_search_items)
        ent_search = ttk.Entry(top_items_frame, textvariable=self.search_var, width=25)
        ent_search.pack(side="right", padx=5)
        ttk.Label(top_items_frame, text="ðŸ” Buscar:").pack(side="right")
        
        tree_items_frame = ttk.Frame(frame_items)
        tree_items_frame.pack(fill="both", expand=True, pady=5)
        
        columns = ("name", "price", "status", "langs", "tags", "allergens")
        self.tree_items = ttk.Treeview(tree_items_frame, columns=columns, show="headings", selectmode="browse")
        self.tree_items.heading("name", text="Nombre")
        self.tree_items.heading("price", text="Precio (â‚¬) âœŽ")
        self.tree_items.heading("status", text="Estado")
        self.tree_items.heading("langs", text="TraducciÃ³n")
        self.tree_items.heading("tags", text="Etiquetas")
        self.tree_items.heading("allergens", text="AlÃ©rgenos")
        self.tree_items.column("name", width=200)
        self.tree_items.column("price", width=80, anchor="center")
        self.tree_items.column("status", width=80, anchor="center")
        self.tree_items.column("langs", width=90, anchor="center")
        self.tree_items.column("tags", width=90, anchor="center")
        self.tree_items.column("allergens", width=120, anchor="center")
        self.tree_items.pack(side="left", fill="both", expand=True)
        self.tree_items.bind("<ButtonPress-1>", self.on_item_drag_start)
        self.tree_items.bind("<ButtonRelease-1>", self.on_item_drag_release)
        self.tree_items.bind("<Double-1>", self.on_item_double_click)
        self.tree_items.bind("<ButtonRelease-1>", self.on_item_single_click_price, add="+")
        
        # Reorder buttons for items
        item_order_frame = ttk.Frame(tree_items_frame)
        item_order_frame.pack(side="right", fill="y", padx=5)
        ttk.Button(item_order_frame, text="â¬†", width=3, command=self.move_item_up).pack(pady=2)
        ttk.Button(item_order_frame, text="â¬‡", width=3, command=self.move_item_down).pack(pady=2)

        btn_item_frame = ttk.Frame(frame_items)
        btn_item_frame.pack(fill="x")
        ttk.Button(btn_item_frame, text="âž• AÃ±adir Prod.", command=self.add_item).pack(side="left", expand=True, fill="x")
        ttk.Button(btn_item_frame, text="âœï¸ Editar Prod.", command=self.edit_item).pack(side="left", expand=True, fill="x")
        ttk.Button(btn_item_frame, text="ðŸ—‘ï¸ Eliminar Prod.", command=self.delete_item).pack(side="left", expand=True, fill="x")

        ttk.Label(frame_items, text="ðŸ’¡ Clic en 'Precio' para editar rÃ¡pido Â· Doble clic para editar el producto completo",
                  foreground="gray", font=("Arial", 8)).pack(anchor="w", padx=4, pady=(0, 2))

    def build_splash_tab(self):
        lbl = ttk.Label(self.tab_splash, text="ImÃ¡genes de la animaciÃ³n inicial (combo1.jpg - combo4.jpg)", font=("Arial", 12, "bold"))
        lbl.pack(anchor="w", padx=10, pady=10)
        
        self.var_splash_active = tk.BooleanVar(value=self.menu_data.get("splash_active", True))
        ttk.Checkbutton(self.tab_splash, text="Activar AnimaciÃ³n Inicial (Splash Screen)", variable=self.var_splash_active).pack(anchor="w", padx=20, pady=5)
        
        splash_imgs = self.menu_data.get("splash_imgs", [True]*4)
        self.var_splash_imgs = []
        self.splash_labels = []
        for i in range(1, 5):
            frame = ttk.Frame(self.tab_splash)
            frame.pack(fill="x", padx=20, pady=5)
            
            var = tk.BooleanVar(value=splash_imgs[i-1])
            self.var_splash_imgs.append(var)
            ttk.Checkbutton(frame, text="", variable=var).pack(side="left")
            
            lbl_file = ttk.Label(frame, text=f"combo{i}.jpg:", width=15)
            lbl_file.pack(side="left")
            
            lbl_path = ttk.Label(frame, text="...", width=50)
            lbl_path.pack(side="left", padx=10)
            self.splash_labels.append(lbl_path)
            
            btn = ttk.Button(frame, text="Reemplazar", command=lambda idx=i: self.replace_splash(idx))
            btn.pack(side="left")
            
        self.update_splash_labels()

    def update_splash_labels(self):
        for i in range(1, 5):
            path = os.path.join(ASSETS_DIR, f"combo{i}.jpg")
            if os.path.exists(path):
                self.splash_labels[i-1].config(text=f"Existe ({os.path.getsize(path)//1024} KB)")
            else:
                self.splash_labels[i-1].config(text="Falta imagen")

    def replace_splash(self, idx):
        file_path = filedialog.askopenfilename(title=f"Seleccionar Imagen para combo{idx}.jpg", filetypes=[("ImÃ¡genes", "*.jpg *.jpeg *.png *.webp")])
        if file_path:
            try:
                compress_and_save_image(file_path, f"combo{idx}", force_jpg=True)
                self.update_splash_labels()
                messagebox.showinfo("Ã‰xito", f"Imagen combo{idx}.jpg actualizada correctamente.")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo copiar la imagen:\n{e}")
    def build_menu_dia_tab(self):
        lbl = ttk.Label(self.tab_menu_dia, text="ConfiguraciÃ³n del MenÃº del DÃ­a", font=("Arial", 12, "bold"))
        lbl.pack(anchor="w", padx=10, pady=10)
        md = self.menu_data.get("menu_del_dia", {})
        
        self.var_md_active = tk.BooleanVar(value=md.get("active", False))
        ttk.Checkbutton(self.tab_menu_dia, text="Activar MenÃº del DÃ­a en la portada de la web", variable=self.var_md_active).pack(anchor="w", padx=10, pady=5)
        
        f_price = ttk.Frame(self.tab_menu_dia)
        f_price.pack(fill="x", padx=10, pady=5)
        ttk.Label(f_price, text="Precio Total (â‚¬):").pack(side="left")
        self.ent_md_price = ttk.Entry(f_price, width=10)
        self.ent_md_price.pack(side="left", padx=5)
        self.ent_md_price.insert(0, str(md.get("price", 12.00)))
        
        ttk.Label(self.tab_menu_dia, text="Primeros (separados por coma):").pack(anchor="w", padx=10)
        self.ent_md_primeros = ttk.Entry(self.tab_menu_dia)
        self.ent_md_primeros.pack(fill="x", padx=10, pady=2)
        self.ent_md_primeros.insert(0, md.get("primeros", ""))
        
        ttk.Label(self.tab_menu_dia, text="Segundos (separados por coma):").pack(anchor="w", padx=10)
        self.ent_md_segundos = ttk.Entry(self.tab_menu_dia)
        self.ent_md_segundos.pack(fill="x", padx=10, pady=2)
        self.ent_md_segundos.insert(0, md.get("segundos", ""))
        
        ttk.Label(self.tab_menu_dia, text="Postres (separados por coma):").pack(anchor="w", padx=10)
        self.ent_md_postres = ttk.Entry(self.tab_menu_dia)
        self.ent_md_postres.pack(fill="x", padx=10, pady=2)
        self.ent_md_postres.insert(0, md.get("postres", ""))
        
        ttk.Label(self.tab_menu_dia, text="Incluye (ej: Pan, Bebida y CafÃ©):").pack(anchor="w", padx=10)
        self.ent_md_incluye = ttk.Entry(self.tab_menu_dia)
        self.ent_md_incluye.pack(fill="x", padx=10, pady=2)
        self.ent_md_incluye.insert(0, md.get("includes", "Pan y 1 Bebida"))

    def build_banner_tab(self):
        lbl = ttk.Label(self.tab_banner, text="Aviso Superior (Banner Promocional)", font=("Arial", 12, "bold"))
        lbl.pack(anchor="w", padx=10, pady=10)
        
        banner_data = self.menu_data.get("banner", {})
        
        self.var_banner_active = tk.BooleanVar(value=banner_data.get("active", False))
        ttk.Checkbutton(self.tab_banner, text="Activar Banner Promocional", variable=self.var_banner_active).pack(anchor="w", padx=10, pady=5)
        
        ttk.Label(self.tab_banner, text="Texto del Banner:").pack(anchor="w", padx=10)
        self.ent_banner_text = ttk.Entry(self.tab_banner, width=60)
        self.ent_banner_text.pack(anchor="w", padx=10, pady=2)
        self.ent_banner_text.insert(0, banner_data.get("text", "Â¡Hoy mÃºsica en directo a las 22:00!"))
        
        ttk.Label(self.tab_banner, text="Fecha de Caducidad (YYYY-MM-DD) - Opcional:").pack(anchor="w", padx=10, pady=(10,0))
        self.ent_banner_date = ttk.Entry(self.tab_banner, width=20)
        self.ent_banner_date.pack(anchor="w", padx=10, pady=2)
        self.ent_banner_date.insert(0, banner_data.get("expiration", ""))
        ttk.Label(self.tab_banner, text="* Si dejas la fecha en blanco, el banner nunca caducarÃ¡.\n* Si pones una fecha, el banner desaparecerÃ¡ al terminar ese dÃ­a.").pack(anchor="w", padx=10)

    def build_orders_tab(self):
        lbl = ttk.Label(self.tab_orders, text="ConfiguraciÃ³n del Sistema de Pedidos", font=("Arial", 12, "bold"))
        lbl.pack(anchor="w", padx=10, pady=10)
        
        self.var_orders_enabled = tk.BooleanVar(value=self.menu_data.get("orders_enabled", True))
        ttk.Checkbutton(self.tab_orders, text="Activar Carrito de Pedidos en la web", variable=self.var_orders_enabled).pack(anchor="w", padx=10, pady=5)
        
        f_num = ttk.Frame(self.tab_orders)
        f_num.pack(fill="x", padx=10, pady=5)
        ttk.Label(f_num, text="NÃºmero de WhatsApp (con prefijo del paÃ­s, ej. 34600123456):").pack(side="left")
        self.ent_whatsapp = ttk.Entry(f_num, width=20)
        self.ent_whatsapp.pack(side="left", padx=5)
        self.ent_whatsapp.insert(0, self.menu_data.get("whatsapp_number", "34600000000"))
        
        ttk.Label(self.tab_orders, text="* Si activas esta opciÃ³n, aparecerÃ¡ un botÃ³n 'ðŸ›’ AÃ±adir' en cada plato.\n* Los clientes podrÃ¡n acumular platos en su carrito e indicar su nÃºmero de mesa.\n* Al final, enviarÃ¡n el pedido directamente a tu WhatsApp con un mensaje estructurado.").pack(anchor="w", padx=10, pady=10)

    # --- TREEVIEW POPULATION ---
    def populate_tree_cats(self):
        selected_id = self.tree_cats.selection()[0] if self.tree_cats.selection() else None
        self.tree_cats.delete(*self.tree_cats.get_children())
        
        for c_idx, cat in enumerate(self.menu_data.get("categories", [])):
            cat_node = self.tree_cats.insert("", "end", iid=f"cat_{c_idx}", text=cat["name"], open=True)
            for s_idx, sub in enumerate(cat.get("subcategories", [])):
                self.tree_cats.insert(cat_node, "end", iid=f"sub_{c_idx}_{s_idx}", text=sub["name"])
                
        if selected_id and self.tree_cats.exists(selected_id):
            self.tree_cats.selection_set(selected_id)
        
        self.on_tree_cat_select(None)

    def on_tree_cat_select(self, event):
        self.tree_items.delete(*self.tree_items.get_children())
        sel = self.tree_cats.selection()
        if not sel: return
        node_id = sel[0]
        
        cat_idx, sub_idx = self.parse_node_id(node_id)
        if cat_idx is None: return
        
        cat = self.menu_data["categories"][cat_idx]
        items = cat.get("items", []) if sub_idx is None else cat.get("subcategories", [])[sub_idx].get("items", [])
        
        for i_idx, item in enumerate(items):
            status = "âŒ Agotado" if item.get("hidden", False) else "âœ… Activo"
            allergens = []
            for key, (icon, _) in ALLERGENS.items():
                if item.get(key): allergens.append(icon)
            tags = []
            for key, (icon, _) in MARKETING_TAGS.items():
                if item.get(key): tags.append(icon)
            spice = item.get("spice_level", 0)
            if spice and spice in SPICE_LEVELS:
                tags.append(SPICE_LEVELS[spice])
            
            langs = []
            if item.get("name_en") or item.get("desc_en"):
                langs.append("ðŸ‡¬ðŸ‡§")
            if item.get("name_fr") or item.get("desc_fr"):
                langs.append("ðŸ‡«ðŸ‡·")
            langs_str = " ".join(langs) if langs else "â€”"
            
            sub_part = sub_idx if sub_idx is not None else "X"
            iid = f"item_{cat_idx}_{sub_part}_{i_idx}"
            price_str = f"{item.get('price', 0):.2f}" if not item.get("multi_prices") else "Varios"
            
            self.tree_items.insert("", "end", iid=iid, values=(
                item["name"], price_str, status, langs_str, "".join(tags), "".join(allergens)
            ))
            
    def do_search_items(self, *args):
        query = self.search_var.get().lower()
        if not query:
            self.on_tree_cat_select(None)
            return
            
        self.tree_items.delete(*self.tree_items.get_children())
        for c_idx, cat in enumerate(self.menu_data.get("categories", [])):
            self._search_and_insert(cat.get("items", []), query, c_idx, None, cat["name"])
            for s_idx, sub in enumerate(cat.get("subcategories", [])):
                self._search_and_insert(sub.get("items", []), query, c_idx, s_idx, f"{cat['name']} > {sub['name']}")

    def _search_and_insert(self, items, query, cat_idx, sub_idx, path_name):
        for i_idx, item in enumerate(items):
            if (query in item["name"].lower() or 
                query in item.get("description", "").lower() or
                query in item.get("name_en", "").lower() or
                query in item.get("desc_en", "").lower() or
                query in item.get("name_fr", "").lower() or
                query in item.get("desc_fr", "").lower()):
                
                status = "âŒ Agotado" if item.get("hidden", False) else "âœ… Activo"
                allergens = []
                for key, (icon, _) in ALLERGENS.items():
                    if item.get(key): allergens.append(icon)
                tags = []
                for key, (icon, _) in MARKETING_TAGS.items():
                    if item.get(key): tags.append(icon)
                spice = item.get("spice_level", 0)
                if spice and spice in SPICE_LEVELS:
                    tags.append(SPICE_LEVELS[spice])
                
                langs = []
                if item.get("name_en") or item.get("desc_en"):
                    langs.append("ðŸ‡¬ðŸ‡§")
                if item.get("name_fr") or item.get("desc_fr"):
                    langs.append("ðŸ‡«ðŸ‡·")
                langs_str = " ".join(langs) if langs else "â€”"
                
                sub_part = sub_idx if sub_idx is not None else "X"
                iid = f"item_{cat_idx}_{sub_part}_{i_idx}"
                price_str = f"{item.get('price', 0):.2f}" if not item.get("multi_prices") else "Varios"
                self.tree_items.insert("", "end", iid=iid, values=(
                    f"[{path_name}] {item['name']}", price_str, status, langs_str, "".join(tags), "".join(allergens)
                ))

    def parse_node_id(self, node_id):
        if node_id.startswith("cat_"):
            return int(node_id.split("_")[1]), None
        elif node_id.startswith("sub_"):
            parts = node_id.split("_")
            return int(parts[1]), int(parts[2])
        return None, None
        
    def get_selected_item_indices(self):
        sel_item = self.tree_items.selection()
        if not sel_item: return None, None, None
        parts = sel_item[0].split("_")
        cat_idx = int(parts[1])
        sub_idx = None if parts[2] == "X" else int(parts[2])
        i_idx = int(parts[3])
        return cat_idx, sub_idx, i_idx

    # --- REORDERING & DRAG DROP ---
    def move_cat_up(self):
        sel = self.tree_cats.selection()
        if not sel: return
        cat_idx, sub_idx = self.parse_node_id(sel[0])
        
        if sub_idx is None:
            if cat_idx > 0:
                cats = self.menu_data["categories"]
                cats[cat_idx], cats[cat_idx-1] = cats[cat_idx-1], cats[cat_idx]
                self.populate_tree_cats()
                self.tree_cats.selection_set(f"cat_{cat_idx-1}")
        else:
            if sub_idx > 0:
                subs = self.menu_data["categories"][cat_idx]["subcategories"]
                subs[sub_idx], subs[sub_idx-1] = subs[sub_idx-1], subs[sub_idx]
                self.populate_tree_cats()
                self.tree_cats.selection_set(f"sub_{cat_idx}_{sub_idx-1}")

    def move_cat_down(self):
        sel = self.tree_cats.selection()
        if not sel: return
        cat_idx, sub_idx = self.parse_node_id(sel[0])
        
        if sub_idx is None:
            cats = self.menu_data["categories"]
            if cat_idx < len(cats) - 1:
                cats[cat_idx], cats[cat_idx+1] = cats[cat_idx+1], cats[cat_idx]
                self.populate_tree_cats()
                self.tree_cats.selection_set(f"cat_{cat_idx+1}")
        else:
            subs = self.menu_data["categories"][cat_idx]["subcategories"]
            if sub_idx < len(subs) - 1:
                subs[sub_idx], subs[sub_idx+1] = subs[sub_idx+1], subs[sub_idx]
                self.populate_tree_cats()
                self.tree_cats.selection_set(f"sub_{cat_idx}_{sub_idx+1}")

    def move_item_up(self):
        cat_idx, sub_idx, i_idx = self.get_selected_item_indices()
        if cat_idx is None or self.search_var.get(): return
        cat = self.menu_data["categories"][cat_idx]
        items_list = cat["items"] if sub_idx is None else cat["subcategories"][sub_idx]["items"]
        if i_idx > 0:
            items_list[i_idx], items_list[i_idx-1] = items_list[i_idx-1], items_list[i_idx]
            self.on_tree_cat_select(None)
            self.tree_items.selection_set(f"item_{cat_idx}_{sub_idx if sub_idx is not None else 'X'}_{i_idx-1}")

    def move_item_down(self):
        cat_idx, sub_idx, i_idx = self.get_selected_item_indices()
        if cat_idx is None or self.search_var.get(): return
        cat = self.menu_data["categories"][cat_idx]
        items_list = cat["items"] if sub_idx is None else cat["subcategories"][sub_idx]["items"]
        if i_idx < len(items_list) - 1:
            items_list[i_idx], items_list[i_idx+1] = items_list[i_idx+1], items_list[i_idx]
            self.on_tree_cat_select(None)
            self.tree_items.selection_set(f"item_{cat_idx}_{sub_idx if sub_idx is not None else 'X'}_{i_idx+1}")

    def on_cat_drag_start(self, event):
        self._drag_cat = self.tree_cats.identify_row(event.y)
        
    def on_cat_drag_release(self, event):
        if not hasattr(self, '_drag_cat') or not self._drag_cat: return
        target_cat = self.tree_cats.identify_row(event.y)
        if not target_cat or target_cat == self._drag_cat: return
        cat_idx_s, sub_idx_s = self.parse_node_id(self._drag_cat)
        cat_idx_t, sub_idx_t = self.parse_node_id(target_cat)
        if cat_idx_s is None or cat_idx_t is None: return
        if sub_idx_s is None and sub_idx_t is None:
            cat = self.menu_data["categories"].pop(cat_idx_s)
            self.menu_data["categories"].insert(cat_idx_t, cat)
            self.populate_tree_cats()
            self.tree_cats.selection_set(f"cat_{cat_idx_t}")
        elif sub_idx_s is not None and sub_idx_t is not None and cat_idx_s == cat_idx_t:
            subs = self.menu_data["categories"][cat_idx_s]["subcategories"]
            sub = subs.pop(sub_idx_s)
            subs.insert(sub_idx_t, sub)
            self.populate_tree_cats()
            self.tree_cats.selection_set(f"sub_{cat_idx_t}_{sub_idx_t}")

    def on_item_drag_start(self, event):
        if self.search_var.get(): return
        column = self.tree_items.identify_column(event.x)
        if column == "#2":
            self._drag_item = None
            return
        self._drag_item = self.tree_items.identify_row(event.y)
        
    def on_item_drag_release(self, event):
        if self.search_var.get() or not hasattr(self, '_drag_item') or not self._drag_item: return
        target_item = self.tree_items.identify_row(event.y)
        if not target_item or target_item == self._drag_item: return
        parts_src = self._drag_item.split("_")
        parts_dst = target_item.split("_")
        if len(parts_src) < 4 or len(parts_dst) < 4: return
        cat_src = int(parts_src[1])
        sub_src = None if parts_src[2] == "X" else int(parts_src[2])
        i_src = int(parts_src[3])
        cat_dst = int(parts_dst[1])
        sub_dst = None if parts_dst[2] == "X" else int(parts_dst[2])
        i_dst = int(parts_dst[3])
        if cat_src != cat_dst or sub_src != sub_dst: return
        cat = self.menu_data["categories"][cat_src]
        items_list = cat["items"] if sub_src is None else cat["subcategories"][sub_src]["items"]
        item = items_list.pop(i_src)
        items_list.insert(i_dst, item)
        self.on_tree_cat_select(None)
        self.tree_items.selection_set(f"item_{cat_src}_{sub_src if sub_src is not None else 'X'}_{i_dst}")

    # --- CATEGORY CRUD ---
    def add_category(self):
        self.show_category_dialog()
        
    def add_subcategory(self):
        sel = self.tree_cats.selection()
        if not sel: return messagebox.showwarning("Aviso", "Selecciona una categorÃ­a primero.")
        cat_idx, _ = self.parse_node_id(sel[0])
        self.show_subcategory_dialog(cat_idx)

    def edit_category(self):
        sel = self.tree_cats.selection()
        if not sel: return
        cat_idx, sub_idx = self.parse_node_id(sel[0])
        if sub_idx is None:
            self.show_category_dialog(cat_idx)
        else:
            self.show_subcategory_dialog(cat_idx, sub_idx)

    def delete_category(self):
        sel = self.tree_cats.selection()
        if not sel: return
        cat_idx, sub_idx = self.parse_node_id(sel[0])
        
        if sub_idx is None:
            name = self.menu_data["categories"][cat_idx]["name"]
            if messagebox.askyesno("Confirmar", f"Â¿Eliminar categorÃ­a entera '{name}'?"):
                del self.menu_data["categories"][cat_idx]
                self.populate_tree_cats()
        else:
            name = self.menu_data["categories"][cat_idx]["subcategories"][sub_idx]["name"]
            if messagebox.askyesno("Confirmar", f"Â¿Eliminar subcategorÃ­a '{name}'?"):
                del self.menu_data["categories"][cat_idx]["subcategories"][sub_idx]
                self.populate_tree_cats()

    def show_category_dialog(self, cat_idx=None):
        dlg = tk.Toplevel(self)
        dlg.title("CategorÃ­a")
        dlg.geometry("480x760")
        dlg.grab_set()
        
        cat = self.menu_data["categories"][cat_idx] if cat_idx is not None else None
        
        ttk.Label(dlg, text="ID de URL (ej: Desayunos):").pack(pady=2)
        ent_id = ttk.Entry(dlg)
        ent_id.pack(pady=2, fill="x", padx=10)
        
        ttk.Label(dlg, text="Nombre visible (ES):").pack(pady=2)
        ent_name = ttk.Entry(dlg)
        ent_name.pack(pady=2, fill="x", padx=10)

        # Translations for category name
        frame_trans_cat = ttk.LabelFrame(dlg, text="ðŸŒ Nombre de CategorÃ­a Traducido")
        frame_trans_cat.pack(fill="x", padx=10, pady=4)
        frame_trans_cat.columnconfigure(1, weight=1)

        ttk.Label(frame_trans_cat, text="ðŸ‡¬ðŸ‡§ Nombre EN:").grid(row=0, column=0, sticky="w", padx=6, pady=3)
        ent_name_en_cat = ttk.Entry(frame_trans_cat)
        ent_name_en_cat.grid(row=0, column=1, sticky="ew", padx=6, pady=3)

        ttk.Label(frame_trans_cat, text="ðŸ‡«ðŸ‡· Nombre FR:").grid(row=1, column=0, sticky="w", padx=6, pady=3)
        ent_name_fr_cat = ttk.Entry(frame_trans_cat)
        ent_name_fr_cat.grid(row=1, column=1, sticky="ew", padx=6, pady=3)
        
        ttk.Label(dlg, text="Tema Visual:").pack(pady=2)
        ent_theme = ttk.Combobox(dlg, values=["gold", "ocean", "forest", "lavender"], state="readonly")
        ent_theme.pack(pady=2, fill="x", padx=10)
        ent_theme.set("gold")

        # Horario Inteligente UI
        frame_sched = ttk.LabelFrame(dlg, text="â° Horario Inteligente (MenÃº Inteligente)")
        frame_sched.pack(fill="x", padx=10, pady=4)
        
        var_sched_enabled = tk.BooleanVar(value=False)
        chk_sched = ttk.Checkbutton(frame_sched, text="Activar ProgramaciÃ³n Horaria", variable=var_sched_enabled)
        chk_sched.grid(row=0, column=0, columnspan=2, sticky="w", padx=6, pady=3)
        
        ttk.Label(frame_sched, text="Hora Inicio (HH:MM):").grid(row=1, column=0, sticky="w", padx=6, pady=3)
        ent_sched_start = ttk.Entry(frame_sched, width=12)
        ent_sched_start.grid(row=1, column=1, sticky="w", padx=6, pady=3)
        ent_sched_start.insert(0, "08:00")
        
        ttk.Label(frame_sched, text="Hora Fin (HH:MM):").grid(row=2, column=0, sticky="w", padx=6, pady=3)
        ent_sched_end = ttk.Entry(frame_sched, width=12)
        ent_sched_end.grid(row=2, column=1, sticky="w", padx=6, pady=3)
        ent_sched_end.insert(0, "16:00")
        
        days_frame = ttk.Frame(frame_sched)
        days_frame.grid(row=3, column=0, columnspan=2, sticky="w", padx=6, pady=3)
        ttk.Label(days_frame, text="DÃ­as:").pack(side="left", padx=2)
        
        days_vars = []
        day_labels = ["L", "M", "X", "J", "V", "S", "D"]
        for d_lbl in day_labels:
            var = tk.BooleanVar(value=True)
            days_vars.append(var)
            ttk.Checkbutton(days_frame, text=d_lbl, variable=var, width=3).pack(side="left")
        
        ttk.Label(dlg, text="Imagen Principal de la CategorÃ­a:").pack(pady=2)
        frame_img = ttk.Frame(dlg)
        frame_img.pack(fill="x", padx=10)
        lbl_img = ttk.Label(frame_img, text=cat.get("image", "Ninguna") if cat else "Ninguna")
        lbl_img.pack(side="left", expand=True, fill="x")
        
        lbl_preview = ttk.Label(dlg)
        lbl_preview.pack(pady=5)
        
        def update_preview(path):
            if path and os.path.exists(path):
                try:
                    img = Image.open(path)
                    img.thumbnail((120, 120))
                    photo = ImageTk.PhotoImage(img)
                    lbl_preview.config(image=photo, text="")
                    lbl_preview.image = photo
                except Exception:
                    lbl_preview.config(image='', text="Sin previsualizaciÃ³n")
            else:
                lbl_preview.config(image='', text="No hay imagen")
                
        selected_img_path = [None]
        def pick_image():
            path = filedialog.askopenfilename(filetypes=[("ImÃ¡genes", "*.jpg *.jpeg *.png *.webp")])
            if path:
                selected_img_path[0] = path
                lbl_img.config(text=os.path.basename(path))
                update_preview(path)
                
        ttk.Button(frame_img, text="Seleccionar", command=pick_image).pack(side="right")
        
        if cat and cat.get("image"):
            full_path = os.path.join(BASE_DIR, cat["image"])
            update_preview(full_path)
        
        if cat:
            ent_id.insert(0, cat.get("id", ""))
            ent_id.config(state="disabled")
            ent_name.insert(0, cat.get("name", ""))
            ent_theme.set(cat.get("theme", "gold"))
            ent_name_en_cat.insert(0, cat.get("name_en", ""))
            ent_name_fr_cat.insert(0, cat.get("name_fr", ""))
            
            # Populate Schedule
            sched = cat.get("schedule", {})
            if sched:
                var_sched_enabled.set(sched.get("enabled", False))
                ent_sched_start.delete(0, tk.END)
                ent_sched_start.insert(0, sched.get("start", "08:00"))
                ent_sched_end.delete(0, tk.END)
                ent_sched_end.insert(0, sched.get("end", "16:00"))
                days_list = sched.get("days", [1,2,3,4,5,6,7])
                for idx, v in enumerate(days_vars):
                    v.set((idx + 1) in days_list)
            
        def save():
            new_id = ent_id.get().strip()
            if not new_id: return
            
            # Schedule validation
            sched_enabled = var_sched_enabled.get()
            sched_start = ent_sched_start.get().strip()
            sched_end = ent_sched_end.get().strip()
            
            time_pat = re.compile(r'^\d{2}:\d{2}$')
            if sched_enabled and (not time_pat.match(sched_start) or not time_pat.match(sched_end)):
                messagebox.showerror("Error", "Las horas deben estar en formato HH:MM (ej: 08:30).")
                return
                
            active_days = []
            for idx, v in enumerate(days_vars):
                if v.get():
                    active_days.append(idx + 1)
                    
            if sched_enabled and not active_days:
                messagebox.showerror("Error", "Debes seleccionar al menos un dÃ­a activo si el horario estÃ¡ habilitado.")
                return
                
            sched_data = {
                "enabled": sched_enabled,
                "start": sched_start,
                "end": sched_end,
                "days": active_days
            }
            
            final_img_path = cat.get("image", f"assets\\cat_{new_id}.jpg") if cat else f"assets\\cat_{new_id}.jpg"
            if selected_img_path[0]:
                final_img_path = compress_and_save_image(selected_img_path[0], f"cat_{new_id}")

            name_en_val = ent_name_en_cat.get().strip()
            name_fr_val = ent_name_fr_cat.get().strip()

            if cat:
                cat["name"] = ent_name.get().strip()
                cat["theme"] = ent_theme.get().strip()
                cat["image"] = final_img_path
                cat["schedule"] = sched_data
                if name_en_val: cat["name_en"] = name_en_val
                if name_fr_val: cat["name_fr"] = name_fr_val
            else:
                new_cat = {
                    "id": new_id,
                    "name": ent_name.get().strip(),
                    "theme": ent_theme.get().strip() or "gold",
                    "items": [], "subcategories": [],
                    "image": final_img_path,
                    "schedule": sched_data
                }
                if name_en_val: new_cat["name_en"] = name_en_val
                if name_fr_val: new_cat["name_fr"] = name_fr_val
                self.menu_data["categories"].append(new_cat)
            self.populate_tree_cats()
            dlg.destroy()
            
        ttk.Button(dlg, text="Guardar", command=save, style="Accent.TButton").pack(pady=10)

    def show_subcategory_dialog(self, cat_idx, sub_idx=None):
        dlg = tk.Toplevel(self)
        dlg.title("SubcategorÃ­a")
        dlg.geometry("420x230")
        dlg.grab_set()
        
        cat = self.menu_data["categories"][cat_idx]
        sub = cat["subcategories"][sub_idx] if sub_idx is not None else None
        
        ttk.Label(dlg, text="Nombre SubcategorÃ­a (ES):").pack(pady=2)
        ent_name = ttk.Entry(dlg)
        ent_name.pack(pady=2, fill="x", padx=10)

        frame_trans_sub = ttk.LabelFrame(dlg, text="ðŸŒ Nombre Traducido (Opcional)")
        frame_trans_sub.pack(fill="x", padx=10, pady=4)
        frame_trans_sub.columnconfigure(1, weight=1)
        ttk.Label(frame_trans_sub, text="ðŸ‡¬ðŸ‡§ EN:").grid(row=0, column=0, sticky="w", padx=6, pady=3)
        ent_name_en_sub = ttk.Entry(frame_trans_sub)
        ent_name_en_sub.grid(row=0, column=1, sticky="ew", padx=6, pady=3)
        ttk.Label(frame_trans_sub, text="ðŸ‡«ðŸ‡· FR:").grid(row=1, column=0, sticky="w", padx=6, pady=3)
        ent_name_fr_sub = ttk.Entry(frame_trans_sub)
        ent_name_fr_sub.grid(row=1, column=1, sticky="ew", padx=6, pady=3)
        
        if sub:
            ent_name.insert(0, sub.get("name", ""))
            ent_name_en_sub.insert(0, sub.get("name_en", ""))
            ent_name_fr_sub.insert(0, sub.get("name_fr", ""))
            
        def save():
            name = ent_name.get().strip()
            if not name: return
            en_val = ent_name_en_sub.get().strip()
            fr_val = ent_name_fr_sub.get().strip()
            if sub:
                sub["name"] = name
                if en_val: sub["name_en"] = en_val
                if fr_val: sub["name_fr"] = fr_val
            else:
                if "subcategories" not in cat: cat["subcategories"] = []
                new_sub = {"id": name, "name": name, "items": []}
                if en_val: new_sub["name_en"] = en_val
                if fr_val: new_sub["name_fr"] = fr_val
                cat["subcategories"].append(new_sub)
            self.populate_tree_cats()
            dlg.destroy()
            
        ttk.Button(dlg, text="Guardar", command=save, style="Accent.TButton").pack(pady=15)

    # --- ITEM CRUD ---
    def add_item(self):
        sel = self.tree_cats.selection()
        if not sel: return messagebox.showwarning("Aviso", "Selecciona una categorÃ­a/subcategorÃ­a.")
        cat_idx, sub_idx = self.parse_node_id(sel[0])
        self.show_item_dialog(cat_idx, sub_idx)

    def edit_item(self):
        cat_idx, sub_idx, i_idx = self.get_selected_item_indices()
        if cat_idx is not None:
            self.show_item_dialog(cat_idx, sub_idx, i_idx)

    def on_item_double_click(self, event):
        """Open full edit dialog on double-click."""
        row_id = self.tree_items.identify_row(event.y)
        if not row_id:
            return
        self.tree_items.selection_set(row_id)
        self.edit_item()

    def on_item_single_click_price(self, event):
        """Inline price editor when clicking the Precio column cell."""
        region = self.tree_items.identify_region(event.x, event.y)
        column = self.tree_items.identify_column(event.x)
        row_id = self.tree_items.identify_row(event.y)

        # column #2 is the 'price' column (1-indexed, #1=name, #2=price, ...)
        if region != "cell" or column != "#2" or not row_id:
            return

        # Don't open inline editor for items with multi-prices (shows "Varios")
        parts = row_id.split("_")
        if len(parts) < 4:
            return
        cat_idx = int(parts[1])
        sub_idx = None if parts[2] == "X" else int(parts[2])
        i_idx = int(parts[3])
        cat = self.menu_data["categories"][cat_idx]
        items_list = cat["items"] if sub_idx is None else cat["subcategories"][sub_idx]["items"]
        item = items_list[i_idx]
        if item.get("multi_prices"):
            return  # multi-price items need full dialog

        # Get the bounding box of the clicked cell
        bbox = self.tree_items.bbox(row_id, column="#2")
        if not bbox:
            return
        x, y, width, height = bbox

        # Create an Entry widget overlaid on the cell
        entry_var = tk.StringVar(value=f"{item.get('price', 0.0):.2f}")
        entry = tk.Entry(self.tree_items, textvariable=entry_var, justify="center",
                         font=("Arial", 10), relief="solid", bd=1,
                         bg="#fffbe6", fg="#333333")
        entry.place(x=x, y=y, width=width, height=height)
        entry.select_range(0, tk.END)
        entry.focus_set()

        def _commit(ev=None):
            val = entry_var.get().replace(',', '.').strip()
            try:
                new_price = float(val)
                item["price"] = new_price
                # Refresh the row in the treeview
                values = list(self.tree_items.item(row_id, "values"))
                values[1] = f"{new_price:.2f}"
                self.tree_items.item(row_id, values=values)
            except ValueError:
                pass  # ignore bad input
            entry.destroy()

        def _cancel(ev=None):
            entry.destroy()

        entry.bind("<Return>", _commit)
        entry.bind("<KP_Enter>", _commit)
        entry.bind("<FocusOut>", _commit)
        entry.bind("<Escape>", _cancel)

    def delete_item(self):
        cat_idx, sub_idx, i_idx = self.get_selected_item_indices()
        if cat_idx is None: return
        cat = self.menu_data["categories"][cat_idx]
        items_list = cat["items"] if sub_idx is None else cat["subcategories"][sub_idx]["items"]
        
        if messagebox.askyesno("Confirmar", f"Â¿Eliminar producto '{items_list[i_idx]['name']}'?"):
            del items_list[i_idx]
            if self.search_var.get():
                self.do_search_items()
            else:
                self.on_tree_cat_select(None)

    def translate_text(self, text, source_lang="es", target_lang="en"):
        import urllib.request
        import urllib.parse
        import json
        import ssl
        try:
            url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(text)}&langpair={source_lang}|{target_lang}"
            ctx = ssl._create_unverified_context()
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=8, context=ctx) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data and data.get("responseData"):
                    return data["responseData"].get("translatedText", "")
        except Exception as e:
            print(f"Translation error: {e}")
        return ""

    def show_item_dialog(self, cat_idx, sub_idx, item_idx=None):
        dlg = tk.Toplevel(self)
        dlg.title("Producto")
        dlg.geometry("650x620")
        dlg.grab_set()
        
        cat = self.menu_data["categories"][cat_idx]
        items_list = cat["items"] if sub_idx is None else cat["subcategories"][sub_idx]["items"]
        item = items_list[item_idx] if item_idx is not None else None
        
        notebook = ttk.Notebook(dlg)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        tab_general = ttk.Frame(notebook)
        tab_trans = ttk.Frame(notebook)
        tab_allergens = ttk.Frame(notebook)
        
        notebook.add(tab_general, text="InformaciÃ³n General")
        notebook.add(tab_trans, text="Traducciones (EN/FR)")
        notebook.add(tab_allergens, text="AlÃ©rgenos y Etiquetas")
        
        # --- TAB: GENERAL ---
        ttk.Label(tab_general, text="Nombre:").pack(pady=(5, 2))
        ent_name = ttk.Entry(tab_general)
        ent_name.pack(pady=2, fill="x", padx=10)
        
        ttk.Label(tab_general, text="DescripciÃ³n:").pack(pady=2)
        ent_desc = tk.Text(tab_general, height=3, font=("Arial", 10))
        ent_desc.pack(pady=2, fill="x", padx=10)
        
        frame_prices_container = ttk.Frame(tab_general)
        frame_prices_container.pack(fill="x", padx=10, pady=5)
        
        var_multi_price = tk.BooleanVar()
        
        frame_price_single = ttk.Frame(frame_prices_container)
        ttk.Label(frame_price_single, text="Precio Ãšnico (â‚¬):").pack(side="left")
        ent_price = ttk.Entry(frame_price_single)
        ent_price.pack(side="left", fill="x", expand=True, padx=5)
        
        frame_price_multi = ttk.Frame(frame_prices_container)
        multi_prices_entries = []
        for i in range(3):
            f = ttk.Frame(frame_price_multi)
            f.pack(fill="x", pady=2)
            ttk.Label(f, text=f"OpciÃ³n {i+1} Nombre:").pack(side="left")
            ent_lbl = ttk.Combobox(f, values=["Tapa", "Media", "RaciÃ³n", "Mini", "Medio", "Entero"], width=10)
            ent_lbl.pack(side="left", padx=5)
            ttk.Label(f, text="Precio (â‚¬):").pack(side="left")
            ent_val = ttk.Entry(f, width=10)
            ent_val.pack(side="left", padx=5)
            multi_prices_entries.append((ent_lbl, ent_val))
            
        def toggle_multi_price():
            if var_multi_price.get():
                frame_price_single.pack_forget()
                frame_price_multi.pack(fill="x", pady=2)
            else:
                frame_price_multi.pack_forget()
                frame_price_single.pack(fill="x", pady=2)
                
        cb_multi = ttk.Checkbutton(frame_prices_container, text="MÃºltiples Precios (Tapa/RaciÃ³n, Entero/Medio...)", variable=var_multi_price, command=toggle_multi_price)
        cb_multi.pack(anchor="w", pady=2)
        frame_price_single.pack(fill="x", pady=2)
        
        var_hidden = tk.BooleanVar()
        ttk.Checkbutton(tab_general, text="ðŸš« Marcar como Agotado / Ocultar temporalmente", variable=var_hidden).pack(pady=5, padx=10, anchor="w")
        
        ttk.Label(tab_general, text="Imagen del Producto (Opcional):").pack(pady=(5, 2))
        frame_img = ttk.Frame(tab_general)
        frame_img.pack(fill="x", padx=10)
        lbl_img = ttk.Label(frame_img, text=item.get("image", "Ninguna") if item else "Ninguna")
        lbl_img.pack(side="left", expand=True, fill="x")
        
        lbl_preview = ttk.Label(tab_general)
        lbl_preview.pack(pady=5)
        
        def update_preview(path):
            if path and os.path.exists(path):
                try:
                    img = Image.open(path)
                    img.thumbnail((100, 100))
                    photo = ImageTk.PhotoImage(img)
                    lbl_preview.config(image=photo, text="")
                    lbl_preview.image = photo
                except Exception:
                    lbl_preview.config(image='', text="Sin previsualizaciÃ³n")
            else:
                lbl_preview.config(image='', text="No hay imagen")
                
        selected_img_path = [None]
        remove_img = [False]
        
        def pick_image():
            path = filedialog.askopenfilename(filetypes=[("ImÃ¡genes", "*.jpg *.jpeg *.png *.webp")])
            if path:
                selected_img_path[0] = path
                remove_img[0] = False
                lbl_img.config(text=os.path.basename(path))
                update_preview(path)
                
        def delete_image():
            selected_img_path[0] = None
            remove_img[0] = True
            lbl_img.config(text="Ninguna")
            update_preview(None)
            
        ttk.Button(frame_img, text="Eliminar", command=delete_image).pack(side="right", padx=5)
        ttk.Button(frame_img, text="Seleccionar", command=pick_image).pack(side="right")
        
        if item and item.get("image"):
            full_path = os.path.join(BASE_DIR, item["image"])
            update_preview(full_path)
            
        # --- TAB: TRANSLATIONS ---
        btn_translate = ttk.Button(tab_trans, text="âœ¨ Auto-traducir desde EspaÃ±ol (vÃ­a Internet)")
        btn_translate.pack(anchor="w", padx=10, pady=10)
        
        frame_trans_en = ttk.LabelFrame(tab_trans, text="ðŸ‡¬ðŸ‡§ TraducciÃ³n InglÃ©s (English)")
        frame_trans_en.pack(fill="x", padx=10, pady=5)
        frame_trans_en.columnconfigure(1, weight=1)
        
        ttk.Label(frame_trans_en, text="Nombre EN:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        ent_name_en = ttk.Entry(frame_trans_en)
        ent_name_en.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        
        ttk.Label(frame_trans_en, text="DescripciÃ³n EN:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        ent_desc_en = ttk.Entry(frame_trans_en)
        ent_desc_en.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        
        frame_trans_fr = ttk.LabelFrame(tab_trans, text="ðŸ‡«ðŸ‡· TraducciÃ³n FrancÃ©s (FranÃ§ais)")
        frame_trans_fr.pack(fill="x", padx=10, pady=5)
        frame_trans_fr.columnconfigure(1, weight=1)
        
        ttk.Label(frame_trans_fr, text="Nombre FR:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        ent_name_fr = ttk.Entry(frame_trans_fr)
        ent_name_fr.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        
        ttk.Label(frame_trans_fr, text="DescripciÃ³n FR:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        ent_desc_fr = ttk.Entry(frame_trans_fr)
        ent_desc_fr.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        
        def start_auto_translate():
            btn_translate.config(state="disabled", text="Traduciendo...")
            es_name = ent_name.get().strip()
            es_desc = ent_desc.get("1.0", tk.END).strip()
            
            def worker():
                en_name = self.translate_text(es_name, "es", "en") if es_name else ""
                en_desc = self.translate_text(es_desc, "es", "en") if es_desc else ""
                fr_name = self.translate_text(es_name, "es", "fr") if es_name else ""
                fr_desc = self.translate_text(es_desc, "es", "fr") if es_desc else ""
                
                def update_gui():
                    if en_name:
                        ent_name_en.delete(0, tk.END)
                        ent_name_en.insert(0, en_name)
                    if en_desc:
                        ent_desc_en.delete(0, tk.END)
                        ent_desc_en.insert(0, en_desc)
                    if fr_name:
                        ent_name_fr.delete(0, tk.END)
                        ent_name_fr.insert(0, fr_name)
                    if fr_desc:
                        ent_desc_fr.delete(0, tk.END)
                        ent_desc_fr.insert(0, fr_desc)
                    btn_translate.config(state="normal", text="âœ¨ Auto-traducir desde EspaÃ±ol (vÃ­a Internet)")
                    messagebox.showinfo("Ã‰xito", "TraducciÃ³n completada correctamente.")
                    
                dlg.after(0, update_gui)
                
            threading.Thread(target=worker, daemon=True).start()
            
        btn_translate.config(command=start_auto_translate)
        
        # --- TAB: ALLERGENS & TAGS ---
        top_frame_al = ttk.Frame(tab_allergens)
        top_frame_al.pack(fill="x", padx=10, pady=5)
        
        def clear_all_allergens():
            if messagebox.askyesno("Confirmar", "Â¿Deseas desmarcar todas las etiquetas y alÃ©rgenos de este producto?"):
                for var in self.allergen_vars.values():
                    var.set(False)
                for var in self.marketing_vars.values():
                    var.set(False)
                self.spice_var.set(0)
                
        ttk.Button(top_frame_al, text="ðŸ§¹ Limpiar Todo", command=clear_all_allergens).pack(side="right")
        
        canvas = tk.Canvas(tab_allergens, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab_allergens, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _on_dialog_close():
            canvas.unbind_all("<MouseWheel>")
            dlg.destroy()
            
        dlg.protocol("WM_DELETE_WINDOW", _on_dialog_close)
        
        frame_al = ttk.LabelFrame(scrollable_frame, text="Etiquetas Especiales y AlÃ©rgenos")
        frame_al.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.allergen_vars = {}
        self.marketing_vars = {}
        
        row = 0; col = 0
        for key, (icon, name) in MARKETING_TAGS.items():
            var = tk.BooleanVar()
            self.marketing_vars[key] = var
            cb = ttk.Checkbutton(frame_al, text=f"{icon} {name}", variable=var)
            cb.grid(row=row, column=col, sticky="w", padx=10, pady=2)
            col += 1
            if col > 2:
                col = 0
                row += 1
                
        row += 1; col = 0
        ttk.Label(frame_al, text="-- Nivel de Picante --", font=("Arial", 9, "bold")).grid(row=row, column=0, columnspan=3, pady=(5,0), sticky="w", padx=5)
        row += 1
        self.spice_var = tk.IntVar(value=0)
        spice_frame = ttk.Frame(frame_al)
        spice_frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=10, pady=4)
        for level, label in [(0, "Sin picante"), (1, "ðŸŒ¶ï¸ Leve"), (2, "ðŸŒ¶ï¸ðŸŒ¶ï¸ Medio"), (3, "ðŸŒ¶ï¸ðŸŒ¶ï¸ðŸŒ¶ï¸ Fuerte")]:
            ttk.Radiobutton(spice_frame, text=label, variable=self.spice_var, value=level).pack(side="left", padx=8)
            
        row += 1; col = 0
        ttk.Label(frame_al, text="-- AlÃ©rgenos --", font=("Arial", 9, "bold")).grid(row=row, column=0, columnspan=3, pady=(5,0), sticky="w", padx=5)
        row += 1; col = 0
        
        for key, (icon, name) in ALLERGENS.items():
            var = tk.BooleanVar()
            self.allergen_vars[key] = var
            cb = ttk.Checkbutton(frame_al, text=f"{icon} {name}", variable=var)
            cb.grid(row=row, column=col, sticky="w", padx=10, pady=2)
            col += 1
            if col > 2:
                col = 0
                row += 1
                
        # Set values
        if item:
            ent_name.insert(0, item.get("name", ""))
            ent_desc.insert("1.0", item.get("description", ""))
            
            if item.get("multi_prices"):
                var_multi_price.set(True)
                for i, mp in enumerate(item["multi_prices"]):
                    if i < 3:
                        multi_prices_entries[i][0].set(mp.get("name", ""))
                        multi_prices_entries[i][1].insert(0, str(mp.get("price", "")))
                toggle_multi_price()
            else:
                var_multi_price.set(False)
                ent_price.insert(0, str(item.get("price", 0.0)))
                toggle_multi_price()
            var_hidden.set(item.get("hidden", False))
            
            for key in ALLERGENS.keys():
                self.allergen_vars[key].set(item.get(key, False))
            for key in MARKETING_TAGS.keys():
                self.marketing_vars[key].set(item.get(key, False))
            self.spice_var.set(item.get("spice_level", 0))
            
            ent_name_en.insert(0, item.get("name_en", ""))
            ent_desc_en.insert(0, item.get("desc_en", ""))
            ent_name_fr.insert(0, item.get("name_fr", ""))
            ent_desc_fr.insert(0, item.get("desc_fr", ""))
            
        def save():
            name = ent_name.get().strip()
            if not name: return messagebox.showwarning("Aviso", "El nombre es obligatorio.")
            
            multi_prices_list = []
            if var_multi_price.get():
                for lbl, val in multi_prices_entries:
                    lname = lbl.get().strip()
                    lval = val.get().replace(',', '.').strip()
                    if lname and lval:
                        try:
                            price_val = float(lval)
                            multi_prices_list.append({"name": lname, "price": price_val})
                        except ValueError:
                            return messagebox.showwarning("Error", f"El precio para '{lname}' no es un nÃºmero vÃ¡lido.")
                if not multi_prices_list:
                    return messagebox.showwarning("Error", "Debes especificar al menos un precio vÃ¡lido si usas mÃºltiples precios.")
                price = 0.0
            else:
                price_str = ent_price.get().replace(',', '.').strip()
                if not price_str:
                    price = 0.0
                else:
                    try:
                        price = float(price_str)
                    except ValueError:
                        return messagebox.showwarning("Error", "El precio Ãºnico especificado no es un nÃºmero vÃ¡lido.")
                        
            clean_id = "".join([c for c in name if c.isalnum()])
            final_img_path = item.get("image", "") if item else ""
            if remove_img[0]:
                final_img_path = ""
            elif selected_img_path[0]:
                final_img_path = compress_and_save_image(selected_img_path[0], f"item_{clean_id}")
                
            new_data = {
                "id": item["id"] if item else name,
                "name": name,
                "description": ent_desc.get("1.0", tk.END).strip(),
                "price": price,
                "hidden": var_hidden.get()
            }
            if var_multi_price.get() and multi_prices_list:
                new_data["multi_prices"] = multi_prices_list
            elif item and "multi_prices" in item:
                item.pop("multi_prices", None)
                
            for key in ALLERGENS.keys():
                val = self.allergen_vars[key].get()
                if val: new_data[key] = True
            for key in MARKETING_TAGS.keys():
                val = self.marketing_vars[key].get()
                if val: new_data[key] = True
            spice = self.spice_var.get()
            if spice > 0:
                new_data["spice_level"] = spice
                
            for field, widget in [("name_en", ent_name_en), ("desc_en", ent_desc_en),
                                  ("name_fr", ent_name_fr), ("desc_fr", ent_desc_fr)]:
                val = widget.get().strip()
                if val:
                    new_data[field] = val
                    
            if final_img_path: new_data["image"] = final_img_path
            
            if item:
                items_list[item_idx] = new_data
            else:
                items_list.append(new_data)
                
            self.on_tree_cat_select(None)
            canvas.unbind_all("<MouseWheel>")
            dlg.destroy()
            
        ttk.Button(dlg, text="Guardar", command=save, style="Accent.TButton").pack(pady=10)

    def get_banner_html(self):
        banner = self.menu_data.get("banner", {})
        if not banner.get("active", False) or not banner.get("text", ""):
            return ""
        
        text = banner.get("text", "").replace('"', '&quot;')
        exp_date = banner.get("expiration", "").strip()
        
        return f"""    <div id="promoBanner" class="promo-banner" style="display: none;">
        <span>{text}</span>
        <button onclick="document.getElementById('promoBanner').style.display='none'" style="background:none; border:none; color:white; font-size:1.2rem; cursor:pointer; margin-left:15px; padding: 0 5px;">âœ•</button>
    </div>
    <script>
        (function() {{
            var exp = "{exp_date}";
            var show = true;
            if (exp) {{
                var parts = exp.split('-');
                if (parts.length === 3) {{
                    var expDate = new Date(parseInt(parts[0]), parseInt(parts[1])-1, parseInt(parts[2]), 23, 59, 59);
                    if (new Date() > expDate) {{ show = false; }}
                }}
            }}
            if (show) {{ document.getElementById('promoBanner').style.display = 'flex'; }}
        }})();
    </script>\n"""

    def get_cart_html(self):
        if not self.menu_data.get("orders_enabled", True):
            return ""
        
        phone = self.menu_data.get("whatsapp_number", "34600000000")
        
        return f"""<!-- CART_START -->
    <!-- Cart FAB -->
    <button id="cartFab" class="cart-fab" style="display: none;" onclick="toggleCart()">
        ðŸ›’
        <span id="cartBadge" class="cart-badge">0</span>
    </button>

    <!-- Cart Overlay & Panel -->
    <div id="cartOverlay" class="cart-overlay" onclick="toggleCart()"></div>
    <div id="cartPanel" class="cart-panel">
        <div class="cart-panel-header">
            <h3>Tu Pedido</h3>
            <button class="cart-close-btn" onclick="toggleCart()">âœ•</button>
        </div>
        <div class="cart-table-row">
            <label for="tableNum">Mesa / Nombre:</label>
            <input type="text" id="tableNum" class="cart-table-input" placeholder="Ej: Mesa 5" value="">
        </div>
        <div id="cartItemsList" class="cart-items-list">
            <!-- Items generated dynamically -->
        </div>
        <div class="cart-footer">
            <div class="cart-total-row">
                <span>Total:</span>
                <span id="cartTotalPrice" class="cart-total-price">0.00 â‚¬</span>
            </div>
            <button class="btn-send-order" onclick="sendWhatsAppOrder()">
                <span>ðŸ’¬ Enviar Pedido por WhatsApp</span>
            </button>
            <button class="btn-clear-cart" onclick="clearCart()">Vaciar Carrito</button>
        </div>
    </div>

    <script>
        // Cart Logic
        let cart = JSON.parse(localStorage.getItem('sergios_cart') || '[]');

        function saveCart() {{
            localStorage.setItem('sergios_cart', JSON.stringify(cart));
            updateCartUI();
        }}

        function addToCart(itemId, itemName, price, optionName = null) {{
            let existing = cart.find(i => i.id === itemId && i.option === optionName);
            if (existing) {{
                existing.qty++;
            }} else {{
                cart.push({{ id: itemId, name: itemName, price: price, option: optionName, qty: 1 }});
            }}
            saveCart();
            
            // Visual feedback
            if (event) {{
                const btn = event.currentTarget;
                btn.classList.add('added');
                const origText = btn.textContent;
                btn.textContent = 'âœ“ AÃ±adido';
                setTimeout(() => {{
                    btn.classList.remove('added');
                    btn.textContent = origText;
                }}, 1200);
            }}
        }}

        function changeQty(index, delta) {{
            cart[index].qty += delta;
            if (cart[index].qty <= 0) {{
                cart.splice(index, 1);
            }}
            saveCart();
        }}

        function removeFromCart(index) {{
            cart.splice(index, 1);
            saveCart();
        }}

        function clearCart() {{
            if (confirm('Â¿Seguro que quieres vaciar el carrito?')) {{
                cart = [];
                saveCart();
            }}
        }}

        function updateCartUI() {{
            const list = document.getElementById('cartItemsList');
            const badge = document.getElementById('cartBadge');
            const fab = document.getElementById('cartFab');
            const totalPriceEl = document.getElementById('cartTotalPrice');
            
            if (!list || !badge || !fab || !totalPriceEl) return;
            
            list.innerHTML = '';
            let total = 0;
            let count = 0;
            
            if (cart.length === 0) {{
                list.innerHTML = '<div class="cart-empty-msg"><span style="font-size: 2.5rem;">ðŸ›’</span><br>Tu carrito estÃ¡ vacÃ­o.<br>Â¡AÃ±ade algunos platos deliciosos!</div>';
                fab.style.display = 'none';
                badge.textContent = '0';
            }} else {{
                fab.style.display = 'flex';
                
                cart.forEach((item, index) => {{
                    const subtotal = item.price * item.qty;
                    total += subtotal;
                    count += item.qty;
                    
                    const optionText = item.option ? ` <span style="font-size:0.75rem; color:var(--primary-color);">(${{item.option}})</span>` : '';
                    
                    const row = document.createElement('div');
                    row.className = 'cart-item-row';
                    row.innerHTML = `
                        <div class="cart-item-info">
                            <div>
                                <div class="cart-item-name">${{item.name}}${{optionText}}</div>
                                <div class="cart-item-unit-price">${{item.price.toFixed(2)}} â‚¬/und</div>
                            </div>
                            <div class="cart-item-subtotal">${{subtotal.toFixed(2)}} â‚¬</div>
                        </div>
                        <div class="cart-item-controls">
                            <button class="cart-qty-btn" onclick="changeQty(${{index}}, -1)">-</button>
                            <span class="cart-qty">${{item.qty}}</span>
                            <button class="cart-qty-btn" onclick="changeQty(${{index}}, 1)">+</button>
                            <button class="cart-remove-btn" onclick="removeFromCart(${{index}})" title="Eliminar">ðŸ—‘ï¸</button>
                        </div>
                    `;
                    list.appendChild(row);
                }});
                
                badge.textContent = count;
            }}
            
            totalPriceEl.textContent = total.toFixed(2) + ' â‚¬';
        }}

        function toggleCart() {{
            document.getElementById('cartPanel').classList.toggle('open');
            document.getElementById('cartOverlay').classList.toggle('open');
        }}

        function sendWhatsAppOrder() {{
            if (cart.length === 0) return;
            
            const tableNum = document.getElementById('tableNum').value.trim();
            if (!tableNum) {{
                alert('Por favor, indica tu nÃºmero de mesa o escribe "Para llevar".');
                document.getElementById('tableNum').focus();
                return;
            }}
            
            let text = `*NUEVO PEDIDO - BAR SERGIO'S*\\n`;
            text += `--------------------------------\\n`;
            text += `ðŸ“ *Mesa/Destino:* ${{tableNum}}\\n`;
            text += `--------------------------------\\n\\n`;
            text += `*Detalle del Pedido:*\\n`;
            
            let total = 0;
            cart.forEach(item => {{
                const subtotal = item.price * item.qty;
                total += subtotal;
                const opt = item.option ? ' (' + item.option + ')' : '';
                text += `â€¢ *${{item.qty}}x* ${{item.name}}${{opt}} - ${{item.price.toFixed(2)}} â‚¬\\n`;
            }});
            
            text += `\\n--------------------------------\\n`;
            text += `ðŸ’° *TOTAL A PAGAR:* *${{total.toFixed(2)}} â‚¬*\\n`;
            text += `--------------------------------\\n\\n`;
            text += `Â¡Muchas gracias! Enseguida lo preparamos. ðŸ™Œ`;
            
            const phone = "{phone}";
            const url = `https://api.whatsapp.com/send?phone=${{phone}}&text=${{encodeURIComponent(text)}}`;
            window.open(url, '_blank');

            // Cerrar panel carrito
            document.getElementById('cartPanel').classList.remove('open');
            document.getElementById('cartOverlay').classList.remove('open');

            // Vaciar carrito
            cart = [];
            saveCart();

            // Mostrar modal de agradecimiento
            document.getElementById('thankYouModal').style.display = 'flex';
        }}

        function closeThankYouModal() {{
            document.getElementById('thankYouModal').style.display = 'none';
        }}

        document.addEventListener('DOMContentLoaded', () => {{
            updateCartUI();
            
            const urlParams = new URLSearchParams(window.location.search);
            const mesaParam = urlParams.get('mesa') || urlParams.get('table');
            if (mesaParam) {{
                localStorage.setItem('sergios_table', 'Mesa ' + mesaParam);
            }}
            
            const savedTable = localStorage.getItem('sergios_table');
            if (savedTable && document.getElementById('tableNum')) {{
                document.getElementById('tableNum').value = savedTable;
            }}
            const tableInput = document.getElementById('tableNum');
            if (tableInput) {{
                tableInput.addEventListener('input', (e) => {{
                    localStorage.setItem('sergios_table', e.target.value.trim());
                }});
            }}
        }});
    </script>

    <!-- Modal Muchas Gracias -->
    <div id="thankYouModal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.65); backdrop-filter:blur(6px); z-index:99999; justify-content:center; align-items:center;">
        <div onclick="event.stopPropagation()" style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 60%,#0f3460 100%); border:1px solid rgba(212,175,55,0.35); border-radius:24px; padding:2.8rem 2.5rem 2.2rem; text-align:center; max-width:340px; width:90%; box-shadow:0 20px 60px rgba(0,0,0,0.5); animation:tyPop 0.45s cubic-bezier(0.34,1.56,0.64,1) both;">
            <div style="font-size:3.8rem; margin-bottom:0.6rem;">&#127881;</div>
            <h2 style="font-family:'Playfair Display',serif; font-size:1.9rem; color:#d4af37; margin:0 0 0.4rem;">&#161;Muchas gracias!</h2>
            <p style="font-family:'Outfit',sans-serif; font-size:1.05rem; color:rgba(255,255,255,0.82); margin:0 0 1.8rem;">Enseguida lo preparamos.</p>
            <button onclick="closeThankYouModal()" style="background:linear-gradient(135deg,#d4af37,#b8962e); color:#0f0f0f; border:none; border-radius:50px; padding:0.75rem 2.2rem; font-family:'Outfit',sans-serif; font-size:1rem; font-weight:700; cursor:pointer;">Perfecto &#10003;</button>
        </div>
    </div>
    <style>@keyframes tyPop {{ from {{ opacity:0; transform:scale(0.7) translateY(30px); }} to {{ opacity:1; transform:scale(1) translateY(0); }} }}</style>
<!-- CART_END -->"""

    # --- HTML GENERATION ---
    def regenerate_html(self):
        categories = self.menu_data.get("categories", [])
        self.update_index_html(categories)
        for cat in categories:
            self.generate_category_html(cat, categories)

    def update_index_html(self, categories):
        if not os.path.exists(INDEX_FILE): return
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            
        splash_active = self.menu_data.get("splash_active", True)
        splash_imgs = self.menu_data.get("splash_imgs", [True]*4)
        
        img_tags = ""
        js_images = []
        
        if splash_active:
            for i, active in enumerate(splash_imgs):
                if active:
                    opacity = "1" if len(js_images) == 0 else "0"
                    img_tags += f"""        <img id="introImg{i+1}" src="assets/combo{i+1}.jpg" alt="Intro {i+1}"
            style="position: absolute; max-width: 100%; max-height: 100%; object-fit: contain; opacity: {opacity}; transition: opacity 0.5s ease;">\n"""
                    js_images.append(f"document.getElementById('introImg{i+1}')")
                    
        if not splash_active or len(js_images) == 0:
            splash_html = f"""    <div id="introOverlay" style="display: none;"></div>
    <script>
        // document.body.style.overflow = 'hidden';
    </script>"""
        else:
            js_images_str = ",\n                ".join(js_images)
            splash_html = f"""    <div id="introOverlay"
        style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #121212; z-index: 9999; display: flex; justify-content: center; align-items: center; transition: opacity 0.5s ease;">
{img_tags}    </div>
    <script>
        document.body.style.overflow = 'hidden';
        (function() {{
            const images = [
                {js_images_str}
            ];
            let current = 0;
            const displayTime = 3000; // 3 seconds per image

            function next() {{
                if (current < images.length - 1) {{
                    if (images[current]) images[current].style.opacity = '0';
                    current++;
                    if (images[current]) images[current].style.opacity = '1';
                    setTimeout(next, displayTime);
                }} else {{
                    const overlay = document.getElementById('introOverlay');
                    if (overlay) {{
                        overlay.style.opacity = '0';
                        setTimeout(() => {{
                            overlay.style.display = 'none';
                            document.body.style.overflow = '';
                        }}, 500);
                    }}
                }}
            }}
            setTimeout(next, displayTime);
        }})();
    </script>"""

        content = re.sub(
            r'<div id="introOverlay".*?</script>',
            splash_html,
            content,
            flags=re.DOTALL
        )
        
        cards_html = []
        md = self.menu_data.get("menu_del_dia", {})
        if md.get("active", False):
            cards_html.append(f"""
                    <div class="category-card" style="background: linear-gradient(135deg, #f6d365 0%, #fda085 100%);" onclick="alert('Consulta con nuestro camarero para pedir el MenÃº del DÃ­a.');">
                        <div style="padding: 20px; text-align: center; color: #fff;">
                            <span style="font-size: 3rem;">ðŸ½ï¸</span>
                            <h2 style="margin: 10px 0; font-family: 'Playfair Display', serif;">MenÃº del DÃ­a</h2>
                            <p style="font-size: 1.2rem; font-weight: bold; margin:0;">{md.get('price', 0):.2f} â‚¬</p>
                            <p style="font-size: 0.9rem; margin-top:10px;">{md.get('primeros','')} <br> {md.get('segundos','')}</p>
                            <small>{md.get('includes','')}</small>
                        </div>
                    </div>""")
                    
        for cat in categories:
            c_es = cat['name'].replace('"', '&quot;')
            c_en = cat.get('name_en', cat['name']).replace('"', '&quot;')
            c_fr = cat.get('name_fr', cat['name']).replace('"', '&quot;')
            
            # Schedule attributes
            sched = cat.get("schedule", {})
            sched_attrs = ""
            if sched and sched.get("enabled", False):
                days_str = ",".join(map(str, sched.get("days", [1,2,3,4,5,6,7])))
                sched_attrs = f' data-sched-enabled="true" data-sched-start="{sched.get("start", "08:00")}" data-sched-end="{sched.get("end", "16:00")}" data-sched-days="{days_str}"'
                
            cards_html.append(f"""
                    <a href="{cat['id']}.html" class="category-card"{sched_attrs}>
                        <img src="{cat.get('image', f'assets/cat_{cat["id"]}.jpg')}" alt="{c_es}" class="category-card-image">
                        <div class="category-card-title"><span class="i18n" data-es="{c_es}" data-en="{c_en}" data-fr="{c_fr}">{c_es}</span></div>
                        <div class="category-card-description"></div>
                    </a>""")

        # Add Roulette Card for Indecisos
        cards_html.append(f"""
                    <a href="ruleta.html" class="category-card roulette-card" style="background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%); border-color: rgba(255, 255, 255, 0.15);">
                        <div style="padding: 2.5rem 1.5rem; text-align: center; color: #fff; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; min-height: 200px;">
                            <span style="font-size: 3.5rem; margin-bottom: 10px; display: inline-block;" class="roulette-emoji">ðŸŽ°</span>
                            <div class="category-card-title" style="color: #fff; padding: 0; margin-bottom: 5px; font-family: 'Playfair Display', serif;"><span class="i18n" data-es="Â¿Indeciso?" data-en="Feeling Indecisive?" data-fr="IndÃ©cis?">Â¿Indeciso?</span></div>
                            <div style="font-size: 0.95rem; opacity: 0.9;"><span class="i18n" data-es="Â¡Deja que la ruleta elija por ti!" data-en="Let the wheel choose for you!" data-fr="Laissez la roue choisir pour vous!">Â¡Deja que la ruleta elija por ti!</span></div>
                        </div>
                    </a>""")

        replacement_grid = '<h2 class="section-title" style="text-align:center; display:block; border:none;"><span class="i18n" data-es="Nuestra Carta" data-en="Our Menu" data-fr="Notre Carte">Nuestra Carta</span></h2>\n<div class="category-grid">\n' + '\n'.join(cards_html) + '\n                </div>\n            </section>'
        content = re.sub(
            r'<h2 class="section-title"[^>]*>.*?</h2>\s*<div class="category-grid">.*?</div>\s*</section>',
            lambda _: replacement_grid,
            content, flags=re.DOTALL
        )
        
        mobile_links = []
        for c in categories:
            c_es = c['name'].replace('"', '&quot;')
            c_en = c.get('name_en', c['name']).replace('"', '&quot;')
            c_fr = c.get('name_fr', c['name']).replace('"', '&quot;')
            mobile_links.append(f'        <a href="{c["id"]}.html" class="mobile-menu-link "><span class="i18n" data-es="{c_es}" data-en="{c_en}" data-fr="{c_fr}">{c_es}</span></a>')
        mobile_links.append('        <a href="ruleta.html" class="mobile-menu-link" style="color: #c084fc; font-weight: 600;"><span class="i18n" data-es="ðŸŽ° Ruleta Indecisos" data-en="ðŸŽ° Indecisive Wheel" data-fr="ðŸŽ° Roue des IndÃ©cis">ðŸŽ° Ruleta Indecisos</span></a>')
            
        banner_html = self.get_banner_html()
        replacement_menu = '<div id="mobileMenu" class="mobile-menu-overlay">\n' + \
            '        <button class="menu-toggle" style="position:absolute; top:1rem; right:1rem; border:none; background:none; font-size:2rem;" onclick="toggleMenu()">âœ•</button>\n' + \
            '\n'.join(mobile_links) + '\n    </div>\n\n' + banner_html + '    <header'
        content = re.sub(
            r'<div id="mobileMenu" class="mobile-menu-overlay">.*?<header',
            lambda _: replacement_menu,
            content, flags=re.DOTALL
        )

        # Remove existing lang switcher to avoid duplicates on repeated saves
        content = re.sub(
            r'\s*<div class="lang-switcher" id="langSwitcher">.*?</script>\s*',
            '\n\n',
            content, flags=re.DOTALL
        )
        content = re.sub(
            r'</header>',
            '</header>\n' + self.get_lang_switcher_html(),
            content, count=1
        )

        # Remove existing cart block to avoid duplicates
        content = re.sub(r'<!-- CART_START -->.*?<!-- CART_END -->', '', content, flags=re.DOTALL)
        
        # Remove existing schedule script to avoid duplicates
        content = re.sub(r'<!-- SCHED_START -->.*?<!-- SCHED_END -->', '', content, flags=re.DOTALL)
        
        # Append cart right before </body>
        cart_html = self.get_cart_html()
        if cart_html:
            content = content.replace('</body>', cart_html + '\n</body>')
            
        sched_script = """<!-- SCHED_START -->
<script>
    document.addEventListener("DOMContentLoaded", function() {
        const now = new Date();
        const currentHour = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
        let currentDay = now.getDay();
        if (currentDay === 0) currentDay = 7;
        
        document.querySelectorAll('.category-card[data-sched-enabled="true"]').forEach(card => {
            const start = card.getAttribute('data-sched-start');
            const end = card.getAttribute('data-sched-end');
            const days = card.getAttribute('data-sched-days').split(',').map(Number);
            
            const isDayActive = days.includes(currentDay);
            const isTimeActive = currentHour >= start && currentHour <= end;
            
            if (!isDayActive || !isTimeActive) {
                card.style.opacity = '0.55';
                card.style.pointerEvents = 'none';
                card.style.position = 'relative';
                if (!card.querySelector('.closed-badge')) {
                    const badge = document.createElement('div');
                    badge.className = 'closed-badge';
                    badge.textContent = `Cerrado (Disponible ${start} - ${end})`;
                    badge.style.position = 'absolute';
                    badge.style.top = '10px';
                    badge.style.right = '10px';
                    badge.style.background = '#e53935';
                    badge.style.color = 'white';
                    badge.style.padding = '4px 8px';
                    badge.style.fontSize = '0.8rem';
                    badge.style.fontWeight = 'bold';
                    badge.style.borderRadius = '4px';
                    badge.style.zIndex = '5';
                    card.appendChild(badge);
                }
            }
        });
    });
</script>
<!-- SCHED_END -->"""
        content = content.replace('</body>', sched_script + '\n    <script src="firebase-sync.js"></script>\n</body>')

        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            f.write(content)

    def render_item(self, item):
        img_html = f"<img src='{item['image']}' alt='{item['name']}' class='item-image' onclick=\"showImageModal('{item['image'].replace('\\', '/')}')\">" if item.get('image') else ""
        details_onclick = f" onclick=\"showImageModal('{item['image'].replace('\\', '/')}')\" style='cursor: zoom-in;'" if item.get('image') else ""
        desc = item.get("description", "")
        
        allergens_html = ""
        for key, (icon, name) in ALLERGENS.items():
            if item.get(key):
                allergens_html += f"<span title='{name}' style='margin-left:5px; font-size:1.1rem; cursor:help;'>{icon}</span>"
                
        marketing_html = ""
        for key, (icon, name) in MARKETING_TAGS.items():
            if item.get(key):
                if key == "tag_novedad":
                    marketing_html += f"<span style='background: linear-gradient(135deg, #ff5722 0%, #ff8f00 100%); color: white; font-size:0.7rem; padding: 2px 8px; border-radius: 10px; margin-left: 5px; vertical-align: middle; text-transform: uppercase; font-weight: bold; box-shadow: 0 2px 4px rgba(255, 87, 34, 0.35);'>{icon} {name}</span>"
                else:
                    marketing_html += f"<span style='background: #ffecb3; color: #ff8f00; font-size:0.7rem; padding: 2px 6px; border-radius: 10px; margin-left: 5px; vertical-align: middle; text-transform: uppercase; font-weight: bold;'>{icon} {name}</span>"
        spice = item.get("spice_level", 0)
        if spice and spice in SPICE_LEVELS:
            spice_icons = SPICE_LEVELS[spice]
            marketing_html += f"<span title='Nivel de picante {spice}/3' style='font-size:0.9rem; margin-left:6px; vertical-align:middle; cursor:help;'>{spice_icons}</span>"
        
        # Style for hidden/sold out items
        extra_style = "opacity: 0.5; filter: grayscale(100%);" if item.get("hidden") else ""
        agotado_badge = "<span style='color: #ff4444; font-size:0.8rem; font-weight:bold; margin-left:10px; border: 1px solid #ff4444; padding:2px 5px; border-radius:4px;'>AGOTADO</span>" if item.get("hidden") else ""

        if item.get("multi_prices"):
            price_html = "<div class='item-price' style='display:flex; flex-direction:column; align-items:flex-end; font-size:1rem; font-weight:normal;'>"
            for mp in item["multi_prices"]:
                price_html += f"<div style='margin-bottom:4px;'><span style='color:#666; font-size:0.85rem; font-weight:bold; text-transform:uppercase;'>{mp['name']}:</span> <span style='font-weight:bold;'>{mp['price']:.2f} â‚¬</span></div>"
            price_html += "</div>"
        else:
            price_html = f"<div class='item-price'>{item.get('price', 0):.2f} â‚¬</div>"

        # Add to cart logic
        orders_enabled = self.menu_data.get("orders_enabled", True)
        add_cart_html = ""
        clean_name = item['name'].replace("'", "\\'")
        
        if orders_enabled and not item.get("hidden"):
            if item.get("multi_prices"):
                options_str = "".join([f'<option value="{mp["name"]}|{mp["price"]}">{mp["name"]} - {mp["price"]:.2f} â‚¬</option>' for mp in item["multi_prices"]])
                select_id = f"select_{item['id'].replace(' ', '_').replace('\'', '_')}"
                add_cart_html = f"""
                <div class="cart-add-row" style="margin-top: 6px;">
                    <select id="{select_id}" class="cart-price-select">
                        {options_str}
                    </select>
                    <button class="btn-add-cart" onclick="let val=document.getElementById('{select_id}').value.split('|'); addToCart('{item['id']}', '{clean_name}', parseFloat(val[1]), val[0])">ðŸ›’ AÃ±adir</button>
                </div>"""
            else:
                add_cart_html = f"""
                <button class="btn-add-cart" style="margin-top: 6px;" onclick="addToCart('{item['id']}', '{clean_name}', {item.get('price', 0)})">ðŸ›’ AÃ±adir</button>"""

        right_col = f"""
                        <div class="item-right-col">
                            {price_html}
                            {add_cart_html}
                        </div>"""

        extra_class = " item-nuevo" if item.get("tag_novedad") else ""
        name_es = item['name'].replace("'", "&#39;")
        name_en = item.get('name_en', name_es).replace("'", "&#39;")
        name_fr = item.get('name_fr', name_es).replace("'", "&#39;")
        desc_es = desc.replace("'", "&#39;")
        desc_en = item.get('desc_en', desc_es).replace("'", "&#39;")
        desc_fr = item.get('desc_fr', desc_es).replace("'", "&#39;")
        
        # Filter attributes
        has_gluten = "true" if item.get("gluten") else "false"
        has_lacteos = "true" if item.get("lacteos") else "false"
        is_vegano = "true" if item.get("vegano") else "false"
        spice_val = str(item.get("spice_level", 0))
        is_recom = "true" if item.get("tag_recomendado") else "false"

        style_attr = f' style="{extra_style}"' if extra_style else ""

        return f"""                    <article class="menu-item{extra_class}"{style_attr} data-gluten="{has_gluten}" data-lacteos="{has_lacteos}" data-vegano="{is_vegano}" data-spice="{spice_val}" data-recomendado="{is_recom}">
                        {img_html}
                        <div class="item-details"{details_onclick}>
                            <h3 class="item-name"><span class="i18n" data-es="{name_es}" data-en="{name_en}" data-fr="{name_fr}">{name_es}</span>{allergens_html}{marketing_html}{agotado_badge}</h3>
                            <p class="item-description"><span class="i18n" data-es="{desc_es}" data-en="{desc_en}" data-fr="{desc_fr}">{desc_es}</span></p>
                        </div>
                        {right_col}
                    </article>"""

    def get_lang_switcher_html(self):
        return """
    <div class="lang-switcher" id="langSwitcher">
        <button id="lang-es" class="lang-btn active" onclick="setLang('es')" title="EspaÃ±ol">ðŸ‡ªðŸ‡¸</button>
        <button id="lang-en" class="lang-btn" onclick="setLang('en')" title="English">ðŸ‡¬ðŸ‡§</button>
        <button id="lang-fr" class="lang-btn" onclick="setLang('fr')" title="FranÃ§ais">ðŸ‡«ðŸ‡·</button>
    </div>
    <script>
        function setLang(lang) {
            localStorage.setItem('menuLang', lang);
            document.querySelectorAll('.i18n').forEach(function(el) {
                var text = el.getAttribute('data-' + lang);
                el.textContent = (text && text.trim()) ? text : el.getAttribute('data-es');
            });
            document.querySelectorAll('.lang-btn').forEach(function(b) { b.classList.remove('active'); });
            var btn = document.getElementById('lang-' + lang);
            if (btn) btn.classList.add('active');
        }
        (function() { setLang(localStorage.getItem('menuLang') || 'es'); })();
    </script>"""

    def generate_category_html(self, cat, all_categories):
        theme = cat.get("theme", "gold")
        sched = cat.get("schedule", {})
        sched_attrs = ""
        if sched and sched.get("enabled", False):
            days_str = ",".join(map(str, sched.get("days", [1,2,3,4,5,6,7])))
            sched_attrs = f' data-sched-enabled="true" data-sched-start="{sched.get("start", "08:00")}" data-sched-end="{sched.get("end", "16:00")}" data-sched-days="{days_str}"'

        html = [f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bar Sergio's - {cat['name']}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="styles.css">
</head>
<body class="theme-{theme}"{sched_attrs}>
    <button class="menu-toggle" onclick="toggleMenu()">â˜°</button>
    <div id="mobileMenu" class="mobile-menu-overlay">
        <button class="menu-toggle" style="position:absolute; top:1rem; right:1rem; border:none; background:none; font-size:2rem;" onclick="toggleMenu()">âœ•</button>"""]

        for c in all_categories:
            active = "active" if c['id'] == cat['id'] else ""
            c_es = c['name'].replace('"', '&quot;')
            c_en = c.get('name_en', c['name']).replace('"', '&quot;')
            c_fr = c.get('name_fr', c['name']).replace('"', '&quot;')
            html.append(f'        <a href="{c["id"]}.html" class="mobile-menu-link {active}"><span class="i18n" data-es="{c_es}" data-en="{c_en}" data-fr="{c_fr}">{c_es}</span></a>')
        html.append('        <a href="ruleta.html" class="mobile-menu-link" style="color: #c084fc; font-weight: 600;"><span class="i18n" data-es="ðŸŽ° Ruleta Indecisos" data-en="ðŸŽ° Indecisive Wheel" data-fr="ðŸŽ° Roue des IndÃ©cis">ðŸŽ° Ruleta Indecisos</span></a>')

        cat_es = cat['name'].replace('"', '&quot;')
        cat_en = cat.get('name_en', cat['name']).replace('"', '&quot;')
        cat_fr = cat.get('name_fr', cat['name']).replace('"', '&quot;')

        html.append(f"""    </div>
{self.get_banner_html()}    <header class="hero">
        <a href="index.html" class="home-btn" title="Volver al inicio">ðŸ </a>
        <div class="hero-content">
            <h1>Bar Sergio's</h1>
            <p class="subtitle"><span class="i18n" data-es="GastronomÃ­a &amp; Buen Ambiente" data-en="Gastronomy &amp; Good Vibes" data-fr="Gastronomie &amp; Bonne Ambiance">GastronomÃ­a &amp; Buen Ambiente</span></p>
        </div>
    </header>
{self.get_lang_switcher_html()}
    <main class="container">
        <div class="filter-container">
            <button id="filter-all" class="filter-btn active" onclick="filterMenu('all')">
                <span class="i18n" data-es="ðŸ½ï¸ Todos" data-en="ðŸ½ï¸ All" data-fr="ðŸ½ï¸ Tous">ðŸ½ï¸ Todos</span>
            </button>
            <button id="filter-gluten" class="filter-btn" onclick="filterMenu('gluten')">
                <span class="i18n" data-es="ðŸŒ¾ Sin Gluten" data-en="ðŸŒ¾ Gluten-Free" data-fr="ðŸŒ¾ Sans Gluten">ðŸŒ¾ Sin Gluten</span>
            </button>
            <button id="filter-lacteos" class="filter-btn" onclick="filterMenu('lacteos')">
                <span class="i18n" data-es="ðŸ¥› Sin Lactosa" data-en="ðŸ¥› Lactose-Free" data-fr="ðŸ¥› Sans Lactose">ðŸ¥› Sin Lactosa</span>
            </button>
            <button id="filter-vegano" class="filter-btn" onclick="filterMenu('vegano')">
                <span class="i18n" data-es="ðŸŒ± Vegano" data-en="ðŸŒ± Vegan" data-fr="ðŸŒ± VÃ©gan">ðŸŒ± Vegano</span>
            </button>
            <button id="filter-picante" class="filter-btn" onclick="filterMenu('picante')">
                <span class="i18n" data-es="ðŸŒ¶ï¸ Picante" data-en="ðŸŒ¶ï¸ Spicy" data-fr="ðŸŒ¶ï¸ Ã‰picÃ©">ðŸŒ¶ï¸ Picante</span>
            </button>
            <button id="filter-especialidad" class="filter-btn" onclick="filterMenu('especialidad')">
                <span class="i18n" data-es="â­ Especialidad" data-en="â­ Specialty" data-fr="â­ SpÃ©cialitÃ©">â­ Especialidad</span>
            </button>
        </div>
        <div class="menu-container">
            <section class="menu-section">
                <h2 class="section-title"><span class="i18n" data-es="{cat_es}" data-en="{cat_en}" data-fr="{cat_fr}">{cat_es}</span></h2>
                <div class="items-list">""")  

        for item in cat.get("items", []):
            if item.get("hidden"):
                continue
            html.append(self.render_item(item))
                    
        html.append("                </div>\n            </section>")
        
        for sub in cat.get("subcategories", []):
            s_es = sub['name'].replace('"', '&quot;')
            s_en = sub.get('name_en', sub['name']).replace('"', '&quot;')
            s_fr = sub.get('name_fr', sub['name']).replace('"', '&quot;')
            html.append(f"""            <section class='menu-section'>
                <h3 class='subsection-title'><span class="i18n" data-es="{s_es}" data-en="{s_en}" data-fr="{s_fr}">{s_es}</span></h3>
                <div class='items-list'>""")
            for item in sub.get("items", []):
                if item.get("hidden"):
                    continue
                html.append(self.render_item(item))
            html.append("                </div>\n            </section>")

        html.append(f"""        </div>
    </main>
    <div id="imageModal" class="image-modal" onclick="hideImageModal()">
        <img id="imageModalImg" class="image-modal-content" alt="Imagen">
    </div>
    <footer>
        <p>&copy; 2026 Bar Sergio's. Todos los derechos reservados.</p>
    </footer>
    <script>
        function toggleMenu() {{ document.getElementById('mobileMenu').classList.toggle('open'); }}
        function showImageModal(src) {{
            var img = document.getElementById('imageModalImg');
            img.src = src;
            document.getElementById('imageModal').classList.add('open');
        }}
        function hideImageModal() {{ document.getElementById('imageModal').classList.remove('open'); }}
        document.addEventListener('keydown', function (e) {{ if (e.key === 'Escape') hideImageModal(); }});

        function filterMenu(type) {{
            document.querySelectorAll('.filter-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            const activeBtn = document.getElementById('filter-' + type);
            if (activeBtn) activeBtn.classList.add('active');

            document.querySelectorAll('.menu-item').forEach(item => {{
                let show = true;
                if (type === 'gluten') {{
                    show = item.getAttribute('data-gluten') !== 'true';
                }} else if (type === 'lacteos') {{
                    show = item.getAttribute('data-lacteos') !== 'true';
                }} else if (type === 'vegano') {{
                    show = item.getAttribute('data-vegano') === 'true';
                }} else if (type === 'picante') {{
                    show = parseInt(item.getAttribute('data-spice') || '0') > 0;
                }} else if (type === 'especialidad') {{
                    show = item.getAttribute('data-recomendado') === 'true';
                }}
                
                if (show) {{
                    item.style.display = '';
                }} else {{
                    item.style.display = 'none';
                }}
            }});
        }}

        document.addEventListener("DOMContentLoaded", function() {{
            const body = document.body;
            if (body.getAttribute('data-sched-enabled') === 'true') {{
                const start = body.getAttribute('data-sched-start');
                const end = body.getAttribute('data-sched-end');
                const days = body.getAttribute('data-sched-days').split(',').map(Number);
                
                const now = new Date();
                const currentHour = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
                let currentDay = now.getDay();
                if (currentDay === 0) currentDay = 7;
                
                const isDayActive = days.includes(currentDay);
                const isTimeActive = currentHour >= start && currentHour <= end;
                
                if (!isDayActive || !isTimeActive) {{
                    const container = document.querySelector('.container');
                    const warning = document.createElement('div');
                    warning.className = 'schedule-warning';
                    warning.innerHTML = `
                        <div class="i18n" 
                             data-es="âš ï¸ Esta secciÃ³n estÃ¡ fuera de su horario de servicio (Disponible de ` + start + ` a ` + end + `). No se pueden realizar pedidos en este momento." 
                             data-en="âš ï¸ This section is outside of its service hours (Available from ` + start + ` to ` + end + `). Orders cannot be placed at this time." 
                             data-fr="âš ï¸ Cette section es en dehors de ses heures de service (Disponible de ` + start + ` Ã  ` + end + `). Les commandes ne peuvent pas Ãªtre passÃ©es pour le moment.">
                             âš ï¸ Esta secciÃ³n estÃ¡ fuera de su horario de servicio (Disponible de ` + start + ` a ` + end + `). No se pueden realizar pedidos en este momento.
                        </div>
                    `;
                    container.insertBefore(warning, container.firstChild);
                    
                    document.querySelectorAll('.btn-add-cart, .cart-add-row').forEach(el => {{
                        el.style.display = 'none';
                    }});
                    
                    if (typeof setLang === 'function') {{
                        setLang(localStorage.getItem('menuLang') || 'es');
                    }}
                }}
            }}
        }});
    </script>
{self.get_cart_html()}
</body>
</html>""")

        cat_file = os.path.join(BASE_DIR, f"{cat['id']}.html")
        with open(cat_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(html))

    # --- ROULETTE CONTROL & API SERVER ---
    def start_api_server(self):
        port = 5000
        self.httpd = None
        while port < 5050:
            try:
                server_address = ('', port)
                outer_self = self
                
                class CustomHandler(SimpleHTTPRequestHandler):
                    def log_message(self, format, *args):
                        pass # Suppress command line output
                        
                    def end_headers(self):
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                        super().end_headers()

                    def do_OPTIONS(self):
                        self.send_response(200)
                        self.end_headers()

                    def do_GET(self):
                        if self.path == '/api/roulette':
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            data = {
                                "prizes_active": outer_self.menu_data.setdefault("roulette", {}).get("prizes_active", True),
                                "prizes": outer_self.menu_data.setdefault("roulette", {}).get("prizes", []),
                                "delivered": load_delivered_prizes()
                            }
                            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
                        else:
                            super().do_GET()

                    def do_POST(self):
                        if self.path == '/api/claim':
                            content_length = int(self.headers.get('Content-Length', 0))
                            post_data = self.rfile.read(content_length)
                            try:
                                data = json.loads(post_data.decode('utf-8'))
                                prize_id = data.get('prize_id')
                                if prize_id:
                                    new_delivered = claim_prize_locally(prize_id)
                                    try:
                                        outer_self.after(0, outer_self.update_prizes_ui)
                                    except Exception:
                                        pass
                                    
                                    self.send_response(200)
                                    self.send_header('Content-Type', 'application/json')
                                    self.end_headers()
                                    self.wfile.write(json.dumps({"status": "success", "delivered": new_delivered}).encode('utf-8'))
                                    return
                            except Exception as e:
                                print("Error processing API claim:", e)
                            self.send_response(400)
                            self.end_headers()

                    def translate_path(self, path):
                        p = super().translate_path(path)
                        rel = os.path.relpath(p, os.getcwd())
                        return os.path.join(BASE_DIR, rel)
                
                self.httpd = HTTPServer(server_address, CustomHandler)
                self.server_port = port
                break
            except Exception:
                port += 1
                
        if self.httpd:
            def run_server():
                self.httpd.serve_forever()
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
        else:
            self.server_port = 0

    def on_closing(self):
        if self.httpd:
            self.httpd.shutdown()
        self.destroy()

    def build_roulette_tab(self):
        lbl = ttk.Label(self.tab_roulette, text="Control de la Ruleta y Premios", font=("Arial", 12, "bold"))
        lbl.pack(anchor="w", padx=10, pady=10)
        
        r_data = self.menu_data.setdefault("roulette", {})
        
        self.var_roulette_prizes_active = tk.BooleanVar(value=r_data.get("prizes_active", True))
        ttk.Checkbutton(self.tab_roulette, text="Activar opciÃ³n de premio en la ruleta", variable=self.var_roulette_prizes_active).pack(anchor="w", padx=10, pady=5)
        
        # Local server info display
        f_server = ttk.Frame(self.tab_roulette)
        f_server.pack(fill="x", padx=10, pady=5)
        self.lbl_server_info = ttk.Label(f_server, text=f"Servidor API local activo en el puerto: {self.server_port}\nURL local para ruleta: http://localhost:{self.server_port}/ruleta.html", foreground="blue")
        self.lbl_server_info.pack(side="left")
        
        # Treeview table
        tree_frame = ttk.Frame(self.tab_roulette)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("id", "name", "quantity", "delivered", "remaining")
        self.tree_prizes = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        self.tree_prizes.heading("id", text="ID")
        self.tree_prizes.heading("name", text="Premio")
        self.tree_prizes.heading("quantity", text="Cant. LÃ­mite")
        self.tree_prizes.heading("delivered", text="Entregados")
        self.tree_prizes.heading("remaining", text="Restantes")
        
        self.tree_prizes.column("id", width=100, anchor="center")
        self.tree_prizes.column("name", width=250, anchor="w")
        self.tree_prizes.column("quantity", width=100, anchor="center")
        self.tree_prizes.column("delivered", width=100, anchor="center")
        self.tree_prizes.column("remaining", width=100, anchor="center")
        
        self.tree_prizes.pack(side="left", fill="both", expand=True)
        
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_prizes.yview)
        self.tree_prizes.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        
        # CRUD buttons
        btn_frame = ttk.Frame(self.tab_roulette)
        btn_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(btn_frame, text="âž• AÃ±adir Premio", command=self.add_roulette_prize).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="âœï¸ Editar Premio", command=self.edit_roulette_prize).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="ðŸ—‘ï¸ Eliminar Premio", command=self.delete_roulette_prize).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="ðŸ”„ Reiniciar Contadores", command=self.reset_roulette_prizes_count).pack(side="right", padx=5)
        
        self.update_prizes_ui()

    def update_prizes_ui(self):
        if not hasattr(self, 'tree_prizes') or not self.tree_prizes:
            return
            
        self.tree_prizes.delete(*self.tree_prizes.get_children())
        prizes = self.menu_data.setdefault("roulette", {}).setdefault("prizes", [])
        delivered = load_delivered_prizes()
        
        for idx, p in enumerate(prizes):
            pid = p.get("id")
            name = p.get("name")
            qty = p.get("quantity", 5)
            deliv = delivered.get(pid, 0)
            rem = max(0, qty - deliv)
            
            self.tree_prizes.insert("", "end", iid=f"prize_{idx}", values=(
                pid, name, qty, deliv, rem
            ))

    def add_roulette_prize(self):
        self.show_roulette_prize_dialog()

    def edit_roulette_prize(self):
        sel = self.tree_prizes.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecciona un premio para editar.")
            return
        idx = int(sel[0].split("_")[1])
        self.show_roulette_prize_dialog(idx)

    def delete_roulette_prize(self):
        sel = self.tree_prizes.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecciona un premio para eliminar.")
            return
        idx = int(sel[0].split("_")[1])
        prizes = self.menu_data.setdefault("roulette", {}).setdefault("prizes", [])
        name = prizes[idx]["name"]
        if messagebox.askyesno("Confirmar", f"Â¿Eliminar premio '{name}'?"):
            del prizes[idx]
            self.update_prizes_ui()

    def show_roulette_prize_dialog(self, prize_idx=None):
        dlg = tk.Toplevel(self)
        dlg.title("Premio de Ruleta")
        dlg.geometry("400x250")
        dlg.grab_set()
        
        prizes = self.menu_data.setdefault("roulette", {}).setdefault("prizes", [])
        prize = prizes[prize_idx] if prize_idx is not None else None
        
        ttk.Label(dlg, text="ID Ãºnico del premio (ej: cafe, cerveza):").pack(pady=5)
        ent_id = ttk.Entry(dlg)
        ent_id.pack(pady=2, fill="x", padx=20)
        
        ttk.Label(dlg, text="Nombre del premio:").pack(pady=5)
        ent_name = ttk.Entry(dlg)
        ent_name.pack(pady=2, fill="x", padx=20)
        
        ttk.Label(dlg, text="Cantidad lÃ­mite (Mensual):").pack(pady=5)
        ent_qty = ttk.Entry(dlg)
        ent_qty.pack(pady=2, fill="x", padx=20)
        
        if prize:
            ent_id.insert(0, prize.get("id", ""))
            ent_id.config(state="disabled")
            ent_name.insert(0, prize.get("name", ""))
            ent_qty.insert(0, str(prize.get("quantity", 5)))
        else:
            ent_qty.insert(0, "5")
            
        def save():
            pid = ent_id.get().strip().lower()
            name = ent_name.get().strip()
            qty_str = ent_qty.get().strip()
            
            if not pid or not name or not qty_str:
                messagebox.showwarning("Error", "Todos los campos son obligatorios.")
                return
            
            try:
                qty = int(qty_str)
                if qty < 0:
                    raise ValueError()
            except ValueError:
                messagebox.showwarning("Error", "La cantidad debe ser un nÃºmero entero mayor o igual a 0.")
                return
                
            if prize_idx is None:
                if any(p.get("id") == pid for p in prizes):
                    messagebox.showwarning("Error", "El ID ya estÃ¡ en uso por otro premio.")
                    return
                    
            if prize_idx is not None:
                prizes[prize_idx]["name"] = name
                prizes[prize_idx]["quantity"] = qty
            else:
                prizes.append({
                    "id": pid,
                    "name": name,
                    "quantity": qty
                })
                
            self.update_prizes_ui()
            dlg.destroy()
            
        ttk.Button(dlg, text="Guardar", command=save, style="Accent.TButton").pack(pady=15)

    def reset_roulette_prizes_count(self):
        if messagebox.askyesno("Confirmar", "Â¿Seguro que quieres reiniciar el contador de todos los premios entregados para este mes?"):
            save_delivered_prizes({})
            self.update_prizes_ui()

    # --- DEPLOYED BACKUPS TAB ---
    def build_backups_tab(self):
        lbl = ttk.Label(self.tab_backups, text="Gestor de Copias de Seguridad (Backups)", font=("Arial", 12, "bold"))
        lbl.pack(anchor="w", padx=10, pady=10)
        
        tree_frame = ttk.Frame(self.tab_backups)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        columns = ("file", "date", "size")
        self.tree_backups = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        self.tree_backups.heading("file", text="Archivo de Respaldo")
        self.tree_backups.heading("date", text="Fecha y Hora")
        self.tree_backups.heading("size", text="TamaÃ±o (KB)")
        
        self.tree_backups.column("file", width=250, anchor="w")
        self.tree_backups.column("date", width=200, anchor="center")
        self.tree_backups.column("size", width=100, anchor="center")
        
        self.tree_backups.pack(side="left", fill="both", expand=True)
        
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_backups.yview)
        self.tree_backups.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        
        btn_frame = ttk.Frame(self.tab_backups)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(btn_frame, text="ðŸ”„ Actualizar Lista", command=self.populate_backups_tree).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="ðŸ’¾ Crear Backup Manual", command=self.create_manual_backup).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="ðŸ“‚ Restaurar Copia", command=self.restore_selected_backup, style="Accent.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="ðŸ—‘ï¸ Eliminar Copia", command=self.delete_selected_backup).pack(side="right", padx=5)
        
        self.populate_backups_tree()

    def populate_backups_tree(self):
        if not hasattr(self, 'tree_backups') or not self.tree_backups:
            return
            
        self.tree_backups.delete(*self.tree_backups.get_children())
        backup_dir = os.path.join(BASE_DIR, "backups")
        if not os.path.exists(backup_dir):
            return
            
        files = [f for f in os.listdir(backup_dir) if f.startswith("menu_backup_") and f.endswith(".json")]
        
        def get_timestamp(filename):
            match = re.search(r'menu_backup_(\d{8})_(\d{6})', filename)
            if match:
                return match.group(1) + "_" + match.group(2)
            return ""
            
        files.sort(key=get_timestamp, reverse=True)
        
        for idx, filename in enumerate(files):
            file_path = os.path.join(backup_dir, filename)
            size_kb = f"{os.path.getsize(file_path) / 1024:.2f}"
            
            match = re.search(r'menu_backup_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', filename)
            if match:
                formatted_date = f"{match.group(3)}/{match.group(2)}/{match.group(1)} {match.group(4)}:{match.group(5)}:{match.group(6)}"
                if "_manual" in filename:
                    formatted_date += " (Manual)"
            else:
                formatted_date = "Desconocida"
                
            self.tree_backups.insert("", "end", iid=f"backup_{idx}", values=(
                filename, formatted_date, size_kb
            ))

    def create_manual_backup(self):
        try:
            backup_dir = os.path.join(BASE_DIR, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"menu_backup_{timestamp}_manual.json"
            backup_path = os.path.join(backup_dir, filename)
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(self.menu_data, f, indent=2, ensure_ascii=False)
                
            self.populate_backups_tree()
            messagebox.showinfo("Ã‰xito", f"Copia de seguridad manual creada como:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear el backup:\n{e}")

    def restore_selected_backup(self):
        sel = self.tree_backups.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecciona una copia de seguridad para restaurar.")
            return
            
        filename = self.tree_backups.item(sel[0], "values")[0]
        backup_path = os.path.join(BASE_DIR, "backups", filename)
        
        if not os.path.exists(backup_path):
            messagebox.showerror("Error", "El archivo de respaldo seleccionado no existe en disco.")
            return
            
        if messagebox.askyesno("Confirmar RestauraciÃ³n", f"Â¿Seguro que quieres restaurar la copia '{filename}'?\nSe perderÃ¡n los cambios actuales no guardados."):
            try:
                if os.path.exists(MENU_FILE):
                    shutil.copy(MENU_FILE, MENU_FILE + ".tmp")
                    
                shutil.copy(backup_path, MENU_FILE)
                self.load_data()
                self.populate_tree_cats()
                self.regenerate_html()
                
                if os.path.exists(MENU_FILE + ".tmp"):
                    os.remove(MENU_FILE + ".tmp")
                    
                messagebox.showinfo("Ã‰xito", "Copia de seguridad restaurada correctamente y sitio web actualizado.")
            except Exception as e:
                if os.path.exists(MENU_FILE + ".tmp"):
                    shutil.copy(MENU_FILE + ".tmp", MENU_FILE)
                    os.remove(MENU_FILE + ".tmp")
                messagebox.showerror("Error", f"Fallo al restaurar backup:\n{e}")

    def delete_selected_backup(self):
        sel = self.tree_backups.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecciona una copia de seguridad para eliminar.")
            return
            
        filename = self.tree_backups.item(sel[0], "values")[0]
        file_path = os.path.join(BASE_DIR, "backups", filename)
        
        if messagebox.askyesno("Confirmar Borrado", f"Â¿Seguro que quieres eliminar permanentemente la copia '{filename}'?"):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                self.populate_backups_tree()
                messagebox.showinfo("Ã‰xito", "Copia de seguridad eliminada.")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar el archivo:\n{e}")

    # --- IMAGE OPTIMIZER TAB ---
    def build_optimizer_tab(self):
        lbl = ttk.Label(self.tab_optimizer, text="Optimizador de ImÃ¡genes y Assets (Acelera tu Web)", font=("Arial", 12, "bold"))
        lbl.pack(anchor="w", padx=10, pady=10)
        
        self.lbl_optimizer_status = ttk.Label(self.tab_optimizer, text="Analiza los assets para ver el estado actual de las imÃ¡genes.", font=("Arial", 10))
        self.lbl_optimizer_status.pack(anchor="w", padx=10, pady=2)
        
        tree_frame = ttk.Frame(self.tab_optimizer)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        columns = ("file", "type", "dimensions", "size", "recommendation")
        self.tree_images = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        self.tree_images.heading("file", text="Nombre de Archivo")
        self.tree_images.heading("type", text="Tipo")
        self.tree_images.heading("dimensions", text="ResoluciÃ³n")
        self.tree_images.heading("size", text="TamaÃ±o")
        self.tree_images.heading("recommendation", text="Estado / RecomendaciÃ³n")
        
        self.tree_images.column("file", width=200, anchor="w")
        self.tree_images.column("type", width=80, anchor="center")
        self.tree_images.column("dimensions", width=120, anchor="center")
        self.tree_images.column("size", width=100, anchor="center")
        self.tree_images.column("recommendation", width=250, anchor="w")
        
        self.tree_images.pack(side="left", fill="both", expand=True)
        
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_images.yview)
        self.tree_images.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        
        btn_frame = ttk.Frame(self.tab_optimizer)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(btn_frame, text="ðŸ” Analizar Assets", command=self.analyze_assets).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="âš¡ Optimizar Seleccionada", command=self.optimize_selected_image).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="ðŸš€ Optimizar Todas las ImÃ¡genes", command=self.optimize_all_images, style="Accent.TButton").pack(side="left", padx=5)
        
        self.analyze_assets()

    def analyze_assets(self):
        if not hasattr(self, 'tree_images') or not self.tree_images:
            return
            
        self.tree_images.delete(*self.tree_images.get_children())
        if not os.path.exists(ASSETS_DIR):
            return
            
        image_extensions = (".jpg", ".jpeg", ".png", ".webp")
        files = [f for f in os.listdir(ASSETS_DIR) if os.path.splitext(f)[1].lower() in image_extensions]
        
        total_size = 0
        total_optimized = 0
        count = 0
        
        for idx, filename in enumerate(files):
            file_path = os.path.join(ASSETS_DIR, filename)
            if not os.path.exists(file_path): continue
            
            size_bytes = os.path.getsize(file_path)
            total_size += size_bytes
            count += 1
            
            ext = os.path.splitext(filename)[1].lower()
            size_str = f"{size_bytes / 1024:.1f} KB" if size_bytes < 1024*1024 else f"{size_bytes / (1024*1024):.2f} MB"
            
            try:
                with Image.open(file_path) as img:
                    width, height = img.size
                    dimensions_str = f"{width}x{height}"
            except Exception:
                dimensions_str = "Error al leer"
                width = height = 0
                
            is_combo = filename.startswith("combo") and filename != "combo4_1.jpg"
            is_logo = filename == "sergios_logo.png"
            
            recommendation = "Excelente"
            
            if is_combo:
                if size_bytes > 200 * 1024 or width > 1000 or height > 1000:
                    recommendation = "Redimensionar / Comprimir (mantener JPG)"
                else:
                    recommendation = "Ya optimizado (animaciÃ³n)"
                    total_optimized += 1
            elif is_logo:
                recommendation = "Logo del bar (mantener PNG/transparencia)"
                total_optimized += 1
            else:
                if ext != ".webp":
                    recommendation = "Convertir a WebP"
                    if size_bytes > 300 * 1024 or width > 800 or height > 800:
                        recommendation += " + Redimensionar"
                else:
                    if size_bytes > 150 * 1024 or width > 800 or height > 800:
                        recommendation = "Redimensionar WebP"
                    else:
                        recommendation = "Optimizado (WebP)"
                        total_optimized += 1
                        
            self.tree_images.insert("", "end", iid=f"img_{idx}", values=(
                filename, ext.upper(), dimensions_str, size_str, recommendation
            ))
            
        size_mb_str = f"{total_size / (1024*1024):.2f} MB"
        self.lbl_optimizer_status.config(
            text=f"Total imÃ¡genes: {count} | TamaÃ±o total: {size_mb_str} | Optimizadas: {total_optimized} de {count}"
        )

    def _optimize_single_image_file(self, filename):
        file_path = os.path.join(ASSETS_DIR, filename)
        if not os.path.exists(file_path):
            return None, 0
            
        ext = os.path.splitext(filename)[1].lower()
        base_name = os.path.splitext(filename)[0]
        
        is_combo = filename.startswith("combo")
        is_logo = filename == "sergios_logo.png"
        
        orig_size = os.path.getsize(file_path)
        
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                
                max_w, max_h = 800, 800
                if is_combo:
                    max_w, max_h = 1000, 1000
                
                if width > max_w or height > max_h:
                    img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
                
                if is_combo:
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    dest_filename = f"{base_name}.jpg"
                    dest_path = os.path.join(ASSETS_DIR, dest_filename)
                    img.save(dest_path, "JPEG", quality=80)
                elif is_logo:
                    dest_filename = f"{base_name}.png"
                    dest_path = os.path.join(ASSETS_DIR, dest_filename)
                    img.save(dest_path, "PNG", optimize=True)
                else:
                    dest_filename = f"{base_name}.webp"
                    dest_path = os.path.join(ASSETS_DIR, dest_filename)
                    img.save(dest_path, "WEBP", quality=80)
                    
            new_size = os.path.getsize(dest_path)
            
            if dest_filename != filename:
                os.remove(file_path)
                
            return dest_filename, orig_size - new_size
        except Exception as e:
            print(f"Error optimizing {filename}: {e}")
            return None, 0

    def optimize_selected_image(self):
        sel = self.tree_images.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecciona una imagen para optimizar.")
            return
            
        filename = self.tree_images.item(sel[0], "values")[0]
        rec = self.tree_images.item(sel[0], "values")[4]
        
        if "Ya optimizado" in rec or "Optimizado" in rec:
            if not messagebox.askyesno("Confirmar", f"La imagen '{filename}' ya parece optimizada. Â¿Optimizar de todas formas?"):
                return
                
        dest_filename, saved_bytes = self._optimize_single_image_file(filename)
        
        if dest_filename:
            if dest_filename != filename:
                self._update_menu_data_image_refs(f"assets/{filename}", f"assets/{dest_filename}")
                with open(MENU_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.menu_data, f, indent=2, ensure_ascii=False)
                js_file = os.path.join(BASE_DIR, 'menu_data.js')
                with open(js_file, 'w', encoding='utf-8') as f:
                    f.write(f"const menuData = {json.dumps(self.menu_data, ensure_ascii=False)};")
                    
            self.regenerate_html()
            self.analyze_assets()
            
            saved_str = f"{saved_bytes / 1024:.1f} KB" if saved_bytes < 1024*1024 else f"{saved_bytes / (1024*1024):.2f} MB"
            messagebox.showinfo("Ã‰xito", f"Imagen optimizada: {filename} -> {dest_filename}\nEspacio recuperado: {saved_str}")
        else:
            messagebox.showerror("Error", f"No se pudo optimizar la imagen {filename}.")

    def _update_menu_data_image_refs(self, old_ref, new_ref):
        old_ref_norm = old_ref.replace('\\', '/')
        new_ref_norm = new_ref.replace('\\', '/')
        
        updated = False
        for cat in self.menu_data.get("categories", []):
            if cat.get("image") and cat["image"].replace('\\', '/') == old_ref_norm:
                cat["image"] = new_ref_norm
                updated = True
            for item in cat.get("items", []):
                if item.get("image") and item["image"].replace('\\', '/') == old_ref_norm:
                    item["image"] = new_ref_norm
                    updated = True
            for sub in cat.get("subcategories", []):
                for item in sub.get("items", []):
                    if item.get("image") and item["image"].replace('\\', '/') == old_ref_norm:
                        item["image"] = new_ref_norm
                        updated = True
        return updated

    def optimize_all_images(self):
        if not os.path.exists(ASSETS_DIR):
            return
            
        image_extensions = (".jpg", ".jpeg", ".png", ".webp")
        files = [f for f in os.listdir(ASSETS_DIR) if os.path.splitext(f)[1].lower() in image_extensions]
        
        if not files:
            messagebox.showinfo("Aviso", "No hay imÃ¡genes para optimizar.")
            return
            
        if messagebox.askyesno("Confirmar OptimizaciÃ³n Global", f"Â¿Seguro que quieres optimizar las {len(files)} imÃ¡genes de assets?\nLos archivos originales pesados serÃ¡n reemplazados y convertidos a WebP."):
            total_saved_bytes = 0
            opt_count = 0
            refs_updated = False
            
            for filename in files:
                file_path = os.path.join(ASSETS_DIR, filename)
                if not os.path.exists(file_path): continue
                
                size_bytes = os.path.getsize(file_path)
                ext = os.path.splitext(filename)[1].lower()
                
                is_combo = filename.startswith("combo")
                is_logo = filename == "sergios_logo.png"
                
                try:
                    with Image.open(file_path) as img:
                        width, height = img.size
                except Exception:
                    width = height = 0
                    
                if is_combo:
                    if size_bytes <= 200 * 1024 and width <= 1000 and height <= 1000:
                        continue
                elif is_logo:
                    continue
                else:
                    if ext == ".webp" and size_bytes <= 150 * 1024 and width <= 800 and height <= 800:
                        continue
                        
                dest_filename, saved_bytes = self._optimize_single_image_file(filename)
                if dest_filename:
                    total_saved_bytes += saved_bytes
                    opt_count += 1
                    if dest_filename != filename:
                        if self._update_menu_data_image_refs(f"assets/{filename}", f"assets/{dest_filename}"):
                            refs_updated = True
                            
            if opt_count > 0:
                if refs_updated:
                    with open(MENU_FILE, 'w', encoding='utf-8') as f:
                        json.dump(self.menu_data, f, indent=2, ensure_ascii=False)
                    js_file = os.path.join(BASE_DIR, 'menu_data.js')
                    with open(js_file, 'w', encoding='utf-8') as f:
                        f.write(f"const menuData = {json.dumps(self.menu_data, ensure_ascii=False)};")
                self.regenerate_html()
                
            self.analyze_assets()
            
            saved_str = f"{total_saved_bytes / 1024:.1f} KB" if total_saved_bytes < 1024*1024 else f"{total_saved_bytes / (1024*1024):.2f} MB"
            messagebox.showinfo("Ã‰xito", f"Se optimizaron {opt_count} imÃ¡genes.\nEspacio recuperado total: {saved_str}")

    # --- QR GENERATOR TAB ---
    def build_qr_tab(self):
        lbl = ttk.Label(self.tab_qr, text="Generador de CÃ³digos QR para Mesas", font=("Arial", 12, "bold"))
        lbl.pack(anchor="w", padx=10, pady=10)
        
        settings_frame = ttk.LabelFrame(self.tab_qr, text="âš™ï¸ ConfiguraciÃ³n")
        settings_frame.pack(fill="x", padx=10, pady=5)
        
        f_url = ttk.Frame(settings_frame)
        f_url.pack(fill="x", padx=10, pady=5)
        ttk.Label(f_url, text="URL Base de la web publicada:").pack(side="left")
        self.ent_qr_url = ttk.Entry(f_url, width=45)
        self.ent_qr_url.pack(side="left", padx=5)
        self.ent_qr_url.insert(0, f"http://localhost:{self.server_port}/")
        
        f_range = ttk.Frame(settings_frame)
        f_range.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(f_range, text="Mesa Inicial:").pack(side="left")
        self.spin_qr_start = ttk.Spinbox(f_range, from_=1, to=100, width=5)
        self.spin_qr_start.pack(side="left", padx=5)
        self.spin_qr_start.set(1)
        
        ttk.Label(f_range, text="Mesa Final:").pack(side="left", padx=15)
        self.spin_qr_end = ttk.Spinbox(f_range, from_=1, to=100, width=5)
        self.spin_qr_end.pack(side="left", padx=5)
        self.spin_qr_end.set(10)
        
        info_lbl = ttk.Label(self.tab_qr, text="* Esta funciÃ³n generarÃ¡ un PDF de tamaÃ±o A4 con una rejilla de 4 tarjetas recortables por pÃ¡gina.\n* Cada tarjeta incluirÃ¡ el logo del bar, el nÃºmero de mesa y el cÃ³digo QR especÃ­fico para esa mesa.\n* Cuando un cliente escanee ese QR, la mesa se pre-rellenarÃ¡ automÃ¡ticamente en el carrito de compras.")
        info_lbl.pack(anchor="w", padx=10, pady=10)
        
        btn_frame = ttk.Frame(self.tab_qr)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(btn_frame, text="ðŸš€ Generar PDF de Mesas", command=self.generate_tables_pdf, style="Accent.TButton").pack(side="left", padx=5)

    def generate_tables_pdf(self):
        base_url = self.ent_qr_url.get().strip()
        if not base_url:
            messagebox.showerror("Error", "La URL Base es obligatoria.")
            return
            
        try:
            start_table = int(self.spin_qr_start.get())
            end_table = int(self.spin_qr_end.get())
            if start_table <= 0 or end_table <= 0 or start_table > end_table:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "Los nÃºmeros de mesa deben ser enteros positivos y el final debe ser mayor o igual al inicial.")
            return
            
        try:
            import qrcode
        except ImportError:
            try:
                import subprocess, sys
                messagebox.showinfo("InstalaciÃ³n", "Instalando la librerÃ­a 'qrcode' para Python. Por favor, espera un momento...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "qrcode", "-q"])
                import qrcode
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo instalar la librerÃ­a 'qrcode':\n{e}")
                return
                
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.colors import HexColor
            from reportlab.pdfgen import canvas
        except ImportError:
            messagebox.showerror("Error", "La librerÃ­a 'reportlab' no estÃ¡ instalada. Ejecuta generar_pdf_qr.py primero para instalarla.")
            return
            
        output_pdf = os.path.join(BASE_DIR, "Mesas_QR_BarSergios.pdf")
        
        try:
            c = canvas.Canvas(output_pdf, pagesize=A4)
            width_a4, height_a4 = A4
            
            margin_x = 25
            margin_y = 25
            gap = 15
            card_w = (width_a4 - 2 * margin_x - gap) / 2
            card_h = (height_a4 - 2 * margin_y - gap) / 2
            
            logo_path = os.path.join(ASSETS_DIR, "sergios_logo.png")
            
            for i, table_num in enumerate(range(start_table, end_table + 1)):
                pos = i % 4
                col = pos % 2
                row = pos // 2
                
                x = margin_x + col * (card_w + gap)
                y = height_a4 - margin_y - card_h - row * (card_h + gap)
                
                c.setFillColor(HexColor("#FAFAF7"))
                c.roundRect(x, y, card_w, card_h, 12, fill=1, stroke=0)
                
                c.setStrokeColor(HexColor("#E2D9D0"))
                c.setLineWidth(1.0)
                c.roundRect(x + 4, y + 4, card_w - 8, card_h - 8, 10, fill=0, stroke=1)
                
                c.setStrokeColor(HexColor("#C9A84C"))
                c.setLineWidth(0.6)
                c.roundRect(x + 7, y + 7, card_w - 14, card_h - 14, 8, fill=0, stroke=1)
                
                c.setFillColor(HexColor("#9B2335"))
                c.roundRect(x + 10, y + card_h - 32, card_w - 20, 22, 4, fill=1, stroke=0)
                
                c.setFillColor(HexColor("#FFFFFF"))
                c.setFont("Helvetica-Bold", 10)
                c.drawCentredString(x + card_w / 2, y + card_h - 26, "BAR SERGIO'S")
                
                if os.path.exists(logo_path):
                    c.drawImage(logo_path, x + card_w/2 - 30, y + card_h - 90, width=60, height=50, preserveAspectRatio=True, mask='auto')
                else:
                    c.setFillColor(HexColor("#9B2335"))
                    c.setFont("Helvetica-BoldOblique", 24)
                    c.drawCentredString(x + card_w/2, y + card_h - 75, "Sergio's")
                
                table_url = f"{base_url.rstrip('/')}/index.html?mesa={table_num}"
                qr = qrcode.QRCode(version=1, box_size=8, border=2)
                qr.add_data(table_url)
                qr.make(fit=True)
                qr_img = qr.make_image(fill_color="black", back_color="white")
                
                temp_qr_path = os.path.join(ASSETS_DIR, f"temp_table_qr_{table_num}.png")
                qr_img.save(temp_qr_path)
                
                qr_size = 130
                c.drawImage(temp_qr_path, x + card_w/2 - qr_size/2, y + 90, width=qr_size, height=qr_size)
                
                try:
                    os.remove(temp_qr_path)
                except Exception:
                    pass
                
                c.setFillColor(HexColor("#9B2335"))
                c.setFont("Helvetica-Bold", 16)
                c.drawCentredString(x + card_w/2, y + 60, f"MESA {table_num}")
                
                c.setFillColor(HexColor("#555555"))
                c.setFont("Helvetica", 8)
                c.drawCentredString(x + card_w/2, y + 38, "Apunta la cÃ¡mara de tu mÃ³vil para pedir")
                
                if pos == 3 and table_num < end_table:
                    c.showPage()
                    
            c.save()
            messagebox.showinfo("Ã‰xito", f"PDF de mesas generado correctamente en:\n{output_pdf}")
            
            if sys.platform == "win32":
                os.startfile(output_pdf)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.run(["open", output_pdf])
            else:
                import subprocess
                subprocess.run(["xdg-open", output_pdf])
                
        except Exception as e:
            import traceback
            messagebox.showerror("Error", f"No se pudo generar el PDF:\n{traceback.format_exc()}")

    def on_tab_changed(self, event):
        selected_tab = self.notebook.tab(self.notebook.select(), "text")
        if selected_tab == "Control de Ruleta":
            self.update_prizes_ui()
        elif selected_tab == "Gestor de Backups":
            self.populate_backups_tree()
        elif selected_tab == "Optimizador de ImÃ¡genes":
            self.analyze_assets()

    # --- DEPLOY / GITHUB PAGES TAB ---
    def build_deploy_tab(self):
        lbl = ttk.Label(self.tab_deploy, text="SincronizaciÃ³n y PublicaciÃ³n en GitHub Pages", font=("Arial", 12, "bold"))
        lbl.pack(anchor="w", padx=10, pady=10)

        cfg = self.menu_data.get("github_deploy", {})

        settings_frame = ttk.LabelFrame(self.tab_deploy, text="âš™ï¸ ConfiguraciÃ³n del Repositorio")
        settings_frame.pack(fill="x", padx=10, pady=5)

        self.var_github_enabled = tk.BooleanVar(value=cfg.get("enabled", False))
        chk_enabled = ttk.Checkbutton(settings_frame, text="Habilitar sincronizaciÃ³n con GitHub Pages", variable=self.var_github_enabled)
        chk_enabled.pack(anchor="w", padx=10, pady=5)

        fields_frame = ttk.Frame(settings_frame)
        fields_frame.pack(fill="x", padx=10, pady=5)
        fields_frame.columnconfigure(1, weight=1)

        ttk.Label(fields_frame, text="Usuario de GitHub:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.ent_github_username = ttk.Entry(fields_frame)
        self.ent_github_username.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.ent_github_username.insert(0, cfg.get("username", ""))

        ttk.Label(fields_frame, text="Nombre del Repositorio:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.ent_github_repo = ttk.Entry(fields_frame)
        self.ent_github_repo.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        self.ent_github_repo.insert(0, cfg.get("repo", ""))

        ttk.Label(fields_frame, text="Rama de despliegue (ej. main o gh-pages):").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.ent_github_branch = ttk.Entry(fields_frame)
        self.ent_github_branch.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        self.ent_github_branch.insert(0, cfg.get("branch", "main"))

        ttk.Label(fields_frame, text="Personal Access Token (PAT) de GitHub:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        
        token_frame = ttk.Frame(fields_frame)
        token_frame.grid(row=3, column=1, sticky="ew", padx=5, pady=2)
        token_frame.columnconfigure(0, weight=1)

        self.ent_github_token = ttk.Entry(token_frame, show="*")
        self.ent_github_token.grid(row=0, column=0, sticky="ew")
        self.ent_github_token.insert(0, cfg.get("token", ""))

        def toggle_token_visibility():
            if self.ent_github_token.cget("show") == "*":
                self.ent_github_token.config(show="")
                btn_show.config(text="ðŸ™ˆ Ocultar")
            else:
                self.ent_github_token.config(show="*")
                btn_show.config(text="ðŸ‘ï¸ Mostrar")

        btn_show = ttk.Button(token_frame, text="ðŸ‘ï¸ Mostrar", width=10, command=toggle_token_visibility)
        btn_show.grid(row=0, column=1, padx=(5, 0))

        self.var_github_auto_sync = tk.BooleanVar(value=cfg.get("auto_sync", False))
        chk_auto = ttk.Checkbutton(settings_frame, text="Subir y actualizar automÃ¡ticamente en la nube al guardar la carta", variable=self.var_github_auto_sync)
        chk_auto.pack(anchor="w", padx=10, pady=5)

        log_frame = ttk.LabelFrame(self.tab_deploy, text="ðŸ“‹ Consola de Operaciones / Log")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.txt_deploy_log = tk.Text(log_frame, height=8, font=("Courier New", 9), bg="#1e1e1e", fg="#33ff33", state="disabled")
        self.txt_deploy_log.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.txt_deploy_log.yview)
        scrollbar.pack(side="right", fill="y", pady=5)
        self.txt_deploy_log.config(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(self.tab_deploy)
        btn_frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(btn_frame, text="ðŸ’¾ Guardar ConfiguraciÃ³n", command=self.save_deploy_config).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="â˜ï¸ Desplegar Ahora", command=lambda: self.run_git_deploy(is_auto=False), style="Accent.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="ðŸ§¹ Limpiar Consola", command=self.clear_deploy_log).pack(side="right", padx=5)

    def save_deploy_config(self):
        self.save_data()

    def clear_deploy_log(self):
        self.txt_deploy_log.config(state="normal")
        self.txt_deploy_log.delete("1.0", tk.END)
        self.txt_deploy_log.config(state="disabled")

    def log_deploy(self, text):
        if hasattr(self, 'txt_deploy_log'):
            def update():
                self.txt_deploy_log.config(state="normal")
                self.txt_deploy_log.insert(tk.END, text + "\n")
                self.txt_deploy_log.see(tk.END)
                self.txt_deploy_log.config(state="disabled")
            self.after(0, update)
        else:
            print(text)

    def run_git_deploy(self, is_auto=False):
        cfg = self.menu_data.get("github_deploy", {})
        if not cfg.get("enabled", False):
            if not is_auto:
                messagebox.showwarning("Aviso", "El despliegue con GitHub estÃ¡ desactivado. ActÃ­valo en la pestaÃ±a de configuraciÃ³n.")
            return

        username = cfg.get("username", "").strip()
        repo = cfg.get("repo", "").strip()
        token = cfg.get("token", "").strip()
        branch = cfg.get("branch", "main").strip()

        if not username or not repo or not token:
            if not is_auto:
                messagebox.showerror("Error", "Debes rellenar los campos de usuario, repositorio y token de acceso de GitHub.")
            return

        threading.Thread(target=self.run_git_deploy_worker, args=(is_auto,), daemon=True).start()

    def run_git_deploy_worker(self, is_auto):
        import subprocess
        import sys
        
        cfg = self.menu_data.get("github_deploy", {})
        username = cfg.get("username", "").strip()
        repo = cfg.get("repo", "").strip()
        token = cfg.get("token", "").strip()
        branch = cfg.get("branch", "main").strip()

        self.log_deploy(f"\n--- INICIANDO DESPLIEGUE A GITHUB PAGES ({datetime.now().strftime('%H:%M:%S')}) ---")
        
        def exec_cmd(cmd_list, desc):
            self.log_deploy(f"\n> {desc}...")
            try:
                env = os.environ.copy()
                env["PAGER"] = "cat"
                env["GIT_TERMINAL_PROMPT"] = "0"
                
                clean_cmd_list = []
                for term in cmd_list:
                    if token in term:
                        clean_cmd_list.append(term.replace(token, "[TOKEN_OCULTO]"))
                    else:
                        clean_cmd_list.append(term)
                
                proc = subprocess.Popen(
                    cmd_list,
                    cwd=BASE_DIR,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                stdout, stderr = proc.communicate(timeout=45)
                
                if stdout:
                    stdout_clean = stdout.replace(token, "[TOKEN_OCULTO]")
                    self.log_deploy(stdout_clean.strip())
                if stderr:
                    stderr_clean = stderr.replace(token, "[TOKEN_OCULTO]")
                    self.log_deploy(stderr_clean.strip())
                    
                if proc.returncode != 0:
                    self.log_deploy(f"âš ï¸ Error: CÃ³digo de salida {proc.returncode}")
                    return False
                return True
            except Exception as e:
                self.log_deploy(f"âš ï¸ ExcepciÃ³n: {e}")
                return False

        if not os.path.exists(os.path.join(BASE_DIR, ".git")):
            if not exec_cmd(["git", "init"], "Inicializando repositorio Git local"):
                return
        
        exec_cmd(["git", "config", "user.name", "Bar Sergio Editor"], "Configurando usuario git")
        exec_cmd(["git", "config", "user.email", "editor@barsergios.local"], "Configurando email git")

        remote_url = f"https://{token}@github.com/{username}/{repo}.git"
        exec_cmd(["git", "remote", "remove", "origin"], "Eliminando remote 'origin' previo")
        if not exec_cmd(["git", "remote", "add", "origin", remote_url], "Vinculando repositorio remoto origin"):
            return

        exec_cmd(["git", "branch", "-M", branch], f"Configurando rama activa como '{branch}'")

        if not exec_cmd(["git", "add", "-A"], "Preparando archivos (.gitignore aplicado)"):
            return

        commit_msg = f"ActualizaciÃ³n automÃ¡tica de carta - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        exec_cmd(["git", "commit", "-m", commit_msg], "Creando punto de control (commit)")

        if exec_cmd(["git", "push", "-u", "origin", branch, "--force"], "Subiendo cambios a la nube en GitHub Pages"):
            self.log_deploy("\nðŸŽ‰ Â¡DESPLIEGUE COMPLETADO CON Ã‰XITO! â˜ï¸")
            self.log_deploy(f"Tu carta deberÃ­a estar visible en breve en:")
            self.log_deploy(f"ðŸ‘‰ https://{username}.github.io/{repo}/")
            if not is_auto:
                def show_success():
                    messagebox.showinfo("Despliegue Exitoso", f"SincronizaciÃ³n completada.\nTu carta estarÃ¡ en breve en:\nhttps://{username}.github.io/{repo}/")
                self.after(0, show_success)
        else:
            self.log_deploy("\nâŒ Fallo en la subida a GitHub. Comprueba la configuraciÃ³n de tu Token y Repositorio.")
            if not is_auto:
                def show_fail():
                    messagebox.showerror("Error de Despliegue", "Fallo al sincronizar con GitHub. Comprueba la pestaÃ±a de log.")
                self.after(0, show_fail)


if __name__ == "__main__":
    app = MenuApp()
    style = ttk.Style(app)
    if "clam" in style.theme_names(): style.theme_use("clam")
    app.mainloop()

