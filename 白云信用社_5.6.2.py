
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import json
import random
import shutil
import os
import re
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, TypedDict, Optional, Tuple, Any


# 常量配置
STORAGE_PATH = Path(os.getenv("EXTERNAL_STORAGE", "/storage/emulated/0"))
MAIN_DATA_DIR = STORAGE_PATH / "BaiyunStudio" / "白云信用社"
ENCOURAGEMENT_FILE = MAIN_DATA_DIR / "custom_encouragements.json"
ENCOURAGEMENT_PACK_DIR = MAIN_DATA_DIR / "encouragement_packs"
SETTINGS_FILE = MAIN_DATA_DIR / "global_settings.json"
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
SEARCH_DIRS = [
    STORAGE_PATH / "Download",
    STORAGE_PATH / "storage" / "emulated" / "0",
    STORAGE_PATH,
    STORAGE_PATH / "Download" / "QQ",
    STORAGE_PATH / "AliYunPan" / "文件" / "白云工作室" / "白云信用社"
]


# 枚举类型
class SavingMode(Enum):
    """储蓄模式枚举"""
    ACCUMULATE = "累积存钱模式"
    PER_TARGET = "单目标存钱模式"


# 类型定义
class SavingsData(TypedDict):
    """储蓄数据类型定义"""
    target: float
    current_saved: float
    total_deposits: int
    deposit_dates: List[str]
    deposit_history: List[Dict]
    saving_mode: str  # 新增 saving_mode 键


class GlobalSettings(TypedDict):
    """全局设置类型定义"""
    auto_open_last_bank: bool
    last_opened_bank: Optional[str]
    base_font_size: int
    zoom_factor: float
    history_time_format: str
    history_display_mode: str


# 系统核心功能
def initialize_data() -> SavingsData:
    """初始化储蓄数据"""
    return {
        "target": 0.0,
        "current_saved": 0.0,
        "total_deposits": 0,
        "deposit_dates": [],
        "deposit_history": [],
        "saving_mode": SavingMode.ACCUMULATE.value  # 初始化 saving_mode
    }


def initialize_global_settings() -> GlobalSettings:
    """初始化全局设置"""
    return {
        "auto_open_last_bank": True,
        "last_opened_bank": None,
        "base_font_size": 10,
        "zoom_factor": 1.4,
        "history_time_format": "second",
        "history_display_mode": "all"
    }


def get_data_file(piggy_bank: str) -> Path:
    """获取存钱罐数据文件路径"""
    return MAIN_DATA_DIR / piggy_bank / "data.json"


def get_backup_dir(piggy_bank: str) -> Path:
    """获取存钱罐备份目录路径"""
    return MAIN_DATA_DIR / piggy_bank / "backup"


def load_global_settings() -> GlobalSettings:
    """加载全局设置"""
    if not SETTINGS_FILE.exists():
        return initialize_global_settings()

    try:
        with SETTINGS_FILE.open("r", encoding="utf-8") as file:
            settings = json.load(file)
            # 确保所有字段都存在
            default_settings = initialize_global_settings()
            for key in default_settings:
                if key not in settings:
                    settings[key] = default_settings[key]
            return settings
    except (json.JSONDecodeError, IOError):
        return initialize_global_settings()


def save_global_settings(settings: GlobalSettings) -> bool:
    """保存全局设置"""
    try:
        MAIN_DATA_DIR.mkdir(parents=True, exist_ok=True)
        with SETTINGS_FILE.open("w", encoding="utf-8") as file:
            json.dump(settings, file, indent=2, ensure_ascii=False)
        return True
    except (IOError, OSError):
        return False


def update_last_opened_bank(bank_name: str):
    """更新上次打开的存钱罐"""
    settings = load_global_settings()
    settings["last_opened_bank"] = bank_name
    save_global_settings(settings)


def load_data(piggy_bank: str) -> SavingsData:
    """加载存钱罐数据"""
    data_file = get_data_file(piggy_bank)

    if not data_file.exists():
        return initialize_data()

    try:
        with data_file.open("r", encoding="utf-8") as file:
            data = json.load(file)

            # 确保所有必要键都存在
            initialized_data = initialize_data()
            for key in initialized_data:
                if key not in data:
                    data[key] = initialized_data[key]

            date_dict = {}
            for record in data.get("deposit_history", []):
                date_str = record["date"]
                date_part = date_str.split()[0] if ' ' in date_str else date_str
                date_dict[date_part] = None

            data["deposit_dates"] = list(date_dict.keys())
            return data
    except (json.JSONDecodeError, KeyError, TypeError):
        return initialize_data()


def save_data(piggy_bank: str, data: SavingsData) -> bool:
    """保存存钱罐数据"""
    try:
        data_file = get_data_file(piggy_bank)
        data_dir = data_file.parent
        data_dir.mkdir(parents=True, exist_ok=True)

        backup_dir = get_backup_dir(piggy_bank)
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"{piggy_bank}_backup_{timestamp}.json"

        with data_file.open("w", encoding="utf-8") as f, \
                backup_file.open("w", encoding="utf-8") as bf:
            json.dump(data, f, indent=2, ensure_ascii=False)
            json.dump(data, bf, indent=2, ensure_ascii=False)

        # 限制备份数量（最多保留5个）
        backup_files = list(backup_dir.glob("*.json"))
        if len(backup_files) > 5:
            backup_files.sort(key=os.path.getmtime)
            for old_file in backup_files[:-5]:
                try:
                    os.remove(old_file)
                except OSError:
                    pass

        return True
    except (IOError, OSError, TypeError):
        return False


def list_piggy_banks() -> List[str]:
    """列出所有存钱罐"""
    MAIN_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return [directory.name for directory in MAIN_DATA_DIR.iterdir() 
            if directory.is_dir() and (directory / "data.json").exists()]


def create_piggy_bank(name: str) -> Optional[str]:
    """创建新存钱罐"""
    if not name:
        return None
        
    if re.search(r'[\\/*?:"<>|]', name):
        return None
        
    bank_dir = MAIN_DATA_DIR / name
    if bank_dir.exists():
        return None
    
    try:
        bank_dir.mkdir(parents=True)
        data = initialize_data()
        data_file = get_data_file(name)
        with data_file.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        return name
    except OSError:
        return None


# 激励系统实现
def load_encouragements() -> Tuple[List[str], List[str]]:
    """加载激励语"""
    default_encouragements = [
        "每一分积累都是未来的基石！",
        "积少成多，聚沙成塔！",
        "滴水穿石，非一日之功；积土成山，非斯须之作。",
        "财富如水，一点一滴汇成江海。",
        "省一分钱就是赚一分钱。",
        "储蓄是财富的种子，坚持是成长的阳光。",
    ]
    
    custom_encouragements = []
    try:
        if ENCOURAGEMENT_FILE.exists():
            with ENCOURAGEMENT_FILE.open("r", encoding="utf-8") as file:
                custom_encouragements = json.load(file)
    except (json.JSONDecodeError, IOError):
        pass
    
    return default_encouragements, custom_encouragements


def save_custom_encouragements(encouragements: List[str]) -> bool:
    """保存自定义激励语"""
    try:
        with ENCOURAGEMENT_FILE.open("w", encoding="utf-8") as file:
            json.dump(encouragements, file, ensure_ascii=False, indent=2)
        return True
    except (IOError, TypeError):
        return False


def get_random_encouragement() -> str:
    """获取随机激励语"""
    default_list, custom_list = load_encouragements()
    return random.choice(default_list + custom_list)


def list_encouragement_packs() -> List[str]:
    """列出激励语包"""
    ENCOURAGEMENT_PACK_DIR.mkdir(parents=True, exist_ok=True)
    return [file.stem for file in ENCOURAGEMENT_PACK_DIR.glob("*.hl")]


def load_encouragement_pack(pack_path: Path) -> List[str]:
    """加载激励语包"""
    if not pack_path.exists():
        return []
    
    try:
        with pack_path.open("r", encoding="utf-8") as file:
            return [line.split('*', 1)[-1].strip() 
                    if '*' in line else line.strip()
                    for line in file if line.strip()]
    except (IOError, UnicodeDecodeError):
        return []


def import_encouragement_pack(pack_path: Path) -> bool:
    """导入激励语包"""
    _, custom_encouragements = load_encouragements()
    pack_encouragements = load_encouragement_pack(pack_path)
    
    if not pack_encouragements:
        return False
    
    # 合并并去重
    new_encouragements = list(set(custom_encouragements + pack_encouragements))
    return save_custom_encouragements(new_encouragements)


def list_backup_files(piggy_bank: str, limit: int = None) -> List[Path]:
    """列出备份文件"""
    backup_dir = get_backup_dir(piggy_bank)
    if not backup_dir.exists():
        return []
    
    backup_files = list(backup_dir.glob("*.json"))
    backup_files.sort(key=os.path.getmtime, reverse=True)
    
    if limit is not None and limit > 0:
        return backup_files[:limit]
    
    return backup_files


def restore_backup_file(piggy_bank: str, backup_file: Path) -> bool:
    """从备份文件恢复"""
    try:
        with backup_file.open("r", encoding="utf-8") as file:
            backup_data = json.load(file)
        
        if save_data(piggy_bank, backup_data):
            return True
        return False
    except (IOError, json.JSONDecodeError):
        return False


def auto_discover_encouragement_packs():
    """自动发现激励语包"""
    ENCOURAGEMENT_PACK_DIR.mkdir(parents=True, exist_ok=True)
    existing_packs = {file.stem for file in ENCOURAGEMENT_PACK_DIR.glob("*.hl")}
    
    for search_dir in SEARCH_DIRS:
        if not search_dir.exists():
            continue
            
        for pack_file in search_dir.glob("*.hl"):
            if pack_file.stem in existing_packs:
                continue
                
            try:
                dest_file = ENCOURAGEMENT_PACK_DIR / pack_file.name
                shutil.copy(pack_file, dest_file)
                existing_packs.add(pack_file.stem)
            except (IOError, OSError):
                pass


# 虚拟键盘类
class VirtualKeyboard:
    """虚拟键盘类"""
    def __init__(self, root, target_entry, input_type="number"):
        self.root = root
        self.target_entry = target_entry
        self.input_type = input_type
        self.keyboard_frame = None
        self.active = False
        
        # 添加输入验证
        validate_cmd = root.register(self.validate_input)
        if target_entry:
            target_entry.config(validate="key", validatecommand=(validate_cmd, '%P'))
    
    def show(self):
        """显示键盘"""
        if not self.active:
            self.keyboard_frame = ttk.Frame(self.root, padding=5)
            self.keyboard_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            self.active = True
            self.create_keyboard_buttons()
    
    def hide(self):
        """隐藏键盘"""
        if self.active and self.keyboard_frame:
            self.keyboard_frame.destroy()
            self.keyboard_frame = None
            self.active = False
    
    def set_target(self, target_entry, input_type):
        """设置目标输入框"""
        self.target_entry = target_entry
        self.input_type = input_type
        self.create_keyboard_buttons()
    
    def create_keyboard_buttons(self):
        """创建键盘按钮"""
        # 清除现有键盘按钮
        if self.keyboard_frame:
            for widget in self.keyboard_frame.winfo_children():
                widget.destroy()

        # 根据输入类型决定键盘布局
        if self.input_type == "number":
            self.create_number_buttons()
        else:
            self.create_letter_buttons()
            
        # 添加删除键
        self.add_delete_button()
        
        # 添加关闭按钮
        self.add_close_button()

    def create_number_buttons(self):
        """创建数字键盘"""
        numbers = [
            ('7', '8', '9'),
            ('4', '5', '6'),
            ('1', '2', '3'),
            ('.', '0',)
        ]
        
        for row in numbers:
            frame = ttk.Frame(self.keyboard_frame)
            frame.pack(fill=tk.X, pady=2)
            for num in row:
                btn = ttk.Button(
                    frame,
                    text=num,
                    command=lambda n=num: self.append_to_entry(n),
                    width=5
                )
                btn.pack(side=tk.LEFT, padx=2)

    def create_letter_buttons(self):
        """创建字母键盘"""
        letters = [
            ('Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'),
            ('A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'),
            ('Z', 'X', 'C', 'V', 'B', 'N', 'M')
        ]
        
        for row in letters:
            frame = ttk.Frame(self.keyboard_frame)
            frame.pack(fill=tk.X, pady=2)
            for letter in row:
                btn = ttk.Button(
                    frame,
                    text=letter,
                    command=lambda l=letter: self.append_to_entry(l),
                    width=5
                )
                btn.pack(side=tk.LEFT, padx=2)

        # 添加空格键
        space_frame = ttk.Frame(self.keyboard_frame)
        space_frame.pack(fill=tk.X, pady=2)
        space_btn = ttk.Button(
            space_frame,
            text="空格",
            command=lambda: self.append_to_entry(" "),
            width=15
        )
        space_btn.pack(pady=5)
        
        # 添加数字键盘切换按钮
        toggle_btn = ttk.Button(
            self.keyboard_frame,
            text="切换到数字键盘",
            command=lambda: self.toggle_mode("number")
        )
        toggle_btn.pack(pady=5)

    def add_delete_button(self):
        """添加删除键"""
        frame = ttk.Frame(self.keyboard_frame)
        frame.pack(fill=tk.X, pady=2)
        delete_btn = ttk.Button(
            frame,
            text="⌫",
            command=self.delete_char,
            width=5
        )
        delete_btn.pack(side=tk.LEFT, padx=2)
        
    def add_close_button(self):
        """添加关闭按钮"""
        close_frame = ttk.Frame(self.keyboard_frame)
        close_frame.pack(fill=tk.X, pady=5)
        
        close_btn = ttk.Button(
            close_frame, 
            text="关闭键盘", 
            command=self.hide
        )
        close_btn.pack(pady=5)

    def append_to_entry(self, char):
        """向输入框添加字符"""
        if not self.target_entry:
            return
            
        current_text = self.target_entry.get()
        cursor_pos = self.target_entry.index(tk.INSERT)
        new_text = current_text[:cursor_pos] + char + current_text[cursor_pos:]
        self.target_entry.delete(0, tk.END)
        self.target_entry.insert(0, new_text)
        self.target_entry.icursor(cursor_pos + 1)
        self.target_entry.focus_set()

    def delete_char(self):
        """删除字符"""
        if not self.target_entry:
            return
            
        cursor_pos = self.target_entry.index(tk.INSERT)
        if cursor_pos > 0:
            current_text = self.target_entry.get()
            new_text = current_text[:cursor_pos-1] + current_text[cursor_pos:]
            self.target_entry.delete(0, tk.END)
            self.target_entry.insert(0, new_text)
            self.target_entry.icursor(cursor_pos - 1)
        self.target_entry.focus_set()

    def toggle_mode(self, new_mode):
        """切换键盘模式"""
        self.input_type = new_mode
        self.create_keyboard_buttons()

    def validate_input(self, new_value):
        """验证输入"""
        if self.input_type == "number":
            try:
                if new_value == "" or new_value == ".":
                    return True
                float(new_value)
                return True
            except ValueError:
                return False
        else:
            return True


# 主应用类
class PiggyBankApp:
    """白云信用社主应用"""
    def __init__(self, root):
        self.root = root
        self.root.title("白云信用社 v5.6.2")
        self.root.geometry("1100x750")
        self.root.minsize(1000, 650)
        self.root.configure(bg="#f5f7fa")
        
        # 全屏状态
        self.fullscreen = False
        self.root.bind("<F11>", self.toggle_fullscreen)
        
        # 加载全局设置
        self.settings = load_global_settings()
        self.base_font_size = self.settings["base_font_size"]
        self.zoom_factor = self.settings["zoom_factor"]
        
        # 应用缩放因子
        self.apply_zoom_factor()
        
        # 初始化变量
        self.current_bank = None
        self.bank_data = None
        self.auto_open_var = tk.BooleanVar(value=self.settings["auto_open_last_bank"])
        
        # 初始化标签
        self.bank_name_label = None
        self.target_label = None
        self.balance_label = None
        self.deposit_count_label = None
        self.deposit_days_label = None
        self.current_balance_label = None
        self.target_amount_label = None
        self.current_target_label = None
        self.progress_label = None
        self.target_progress_label = None
        
        # 设置样式
        self.setup_style()
        
        # 初始化界面
        self.init_ui()
        
        # 检查自动打开设置
        self.check_auto_open()
        
        # 启动激励语定时器
        self.update_encouragement()
        
        # 自动发现扩展包
        auto_discover_encouragement_packs()

        # 绑定输入框焦点事件
        self.root.bind("<FocusIn>", self.on_focus_in)
        self.last_focused_entry = None
        self.virtual_keyboard = None

    def apply_zoom_factor(self):
        """应用缩放因子到所有控件"""
        # 计算实际字体大小
        actual_font_size = int(self.base_font_size * self.zoom_factor)
        
        # 设置全局缩放因子
        self.root.tk.call('tk', 'scaling', self.zoom_factor * 1.5)
        
        # 设置全局字体
        self.root.option_add("*Font", f"Arial {actual_font_size}")

    def setup_style(self):
        """设置应用样式"""
        style = ttk.Style()
        style.theme_use("clam")
        
        # 配置基础颜色
        bg_color = "#f5f7fa"
        card_bg = "#ffffff"
        primary_color = "#4a7abc"
        secondary_color = "#6c757d"
        success_color = "#28a745"
        danger_color = "#dc3545"
        accent_color = "#5e72e4"
        
        # 计算字体大小
        actual_font_size = int(self.base_font_size * self.zoom_factor)
        title_font = ("Arial", actual_font_size + 8, "bold")
        subtitle_font = ("Arial", actual_font_size + 4)
        accent_font = ("Arial", actual_font_size + 4, "bold")
        
        # 全局背景
        style.configure(".", background=bg_color)
        style.configure("TFrame", background=bg_color)
        
        # 卡片样式
        style.configure("Card.TFrame", background=card_bg, borderwidth=0, 
                        relief="solid", padding=10, bordercolor="#e0e0e0")
        
        # 标签样式
        style.configure("TLabel", background=bg_color, foreground="#333333")
        style.configure("Title.TLabel", font=title_font, foreground="#2d3748")
        style.configure("Subtitle.TLabel", font=subtitle_font, foreground="#4a5568")
        style.configure("Accent.TLabel", font=accent_font, foreground=accent_color)
        
        # 按钮样式
        style.configure("TButton", padding=8, relief="flat", borderwidth=0, 
                       background=primary_color, foreground="white", 
                       font=("Arial", actual_font_size, "bold"),
                       focusthickness=0, focuscolor="none")
        style.map("TButton", 
                 background=[("active", "#3a6aac"), ("disabled", "#cccccc")],
                 foreground=[("disabled", "#999999")])
        
        style.configure("Primary.TButton", background=primary_color)
        style.map("Primary.TButton", background=[("active", "#3a6aac")])
        
        style.configure("Secondary.TButton", background=secondary_color)
        style.map("Secondary.TButton", background=[("active", "#5a6268")])
        
        style.configure("Success.TButton", background=success_color)
        style.map("Success.TButton", background=[("active", "#218838")])
        
        style.configure("Danger.TButton", background=danger_color)
        style.map("Danger.TButton", background=[("active", "#bd2130")])
        
        # 进度条样式
        style.configure("Horizontal.TProgressbar", thickness=20, background=primary_color, troughcolor="#e2e8f0")
        
        # 输入框样式
        style.configure("TEntry", padding=8, fieldbackground="#ffffff", bordercolor="#cbd5e0", 
                        lightcolor="#e2e8f0", darkcolor="#e2e8f0", relief="flat")
        
        # 笔记本样式
        style.configure("TNotebook", background=bg_color, borderwidth=0)
        style.configure("TNotebook.Tab", padding=[15, 8], background="#e2e8f0", 
                        borderwidth=0, font=("Arial", actual_font_size, "bold"))
        style.map("TNotebook.Tab", background=[("selected", bg_color), ("active", "#cbd5e0")])

    def init_ui(self):
        """初始化用户界面"""
        # 创建工具栏
        self.create_toolbar()
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 20))
        
        # 创建状态栏
        self.status_label = ttk.Label(
            self.root, 
            text="就绪", 
            relief=tk.SUNKEN, 
            anchor=tk.W,
            background="#e2e8f0",
            foreground="#4a5568",
            font=("Arial", 9)
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=0, pady=0)
        
        # 创建左侧导航栏
        self.create_nav_frame()
        
        # 创建右侧内容区域
        self.create_content_frame()
        
        # 更新存钱罐列表
        self.update_bank_list()
        
        # 初始化虚拟键盘
        self.virtual_keyboard = VirtualKeyboard(self.root, None)

    def create_toolbar(self):
        """创建工具栏"""
        toolbar = ttk.Frame(self.root, height=40)
        toolbar.pack(fill=tk.X, padx=20, pady=(10, 0))
        
        # 应用标题
        title = ttk.Label(toolbar, text="白云信用社", font=("Arial", 16, "bold"), 
                         foreground="#4a7abc")
        title.pack(side=tk.LEFT, padx=10)
        
        # 设置按钮
        btn_settings = ttk.Button(
            toolbar, 
            text="设置",
            command=lambda: self.notebook.select(5),
            width=8,
            style="Secondary.TButton"
        )
        btn_settings.pack(side=tk.RIGHT, padx=5)
        
        # 全屏按钮
        fullscreen_btn = ttk.Button(
            toolbar, 
            text="全屏" if not self.fullscreen else "退出全屏",
            command=self.toggle_fullscreen,
            width=8,
            style="Secondary.TButton"
        )
        fullscreen_btn.pack(side=tk.RIGHT, padx=5)

    def toggle_fullscreen(self, event=None):
        """切换全屏模式"""
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)
        return "break"

    def create_nav_frame(self):
        """创建导航框架"""
        nav_frame = ttk.LabelFrame(
            self.main_frame, 
            text="我的存钱罐", 
            padding=(15, 10),
            style="Card.TFrame"
            
        )
        nav_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20), pady=5)
        
        # 存钱罐列表
        self.bank_list = tk.Listbox(
            nav_frame, 
            width=22, 
            height=18,
            selectmode=tk.SINGLE,
            borderwidth=0,
            highlightthickness=0,
            bg="#ffffff",
            font=("Arial", 10)
        )
        scrollbar = ttk.Scrollbar(nav_frame, orient=tk.VERTICAL, command=self.bank_list.yview)
        self.bank_list.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.bank_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.bank_list.bind('<<ListboxSelect>>', self.on_bank_selected)
        
        # 按钮框架
        btn_frame = ttk.Frame(nav_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=(10, 0))
        
        self.btn_create_bank = ttk.Button(
            btn_frame, 
            text="创建新存钱罐", 
            command=self.create_new_bank,
            style="Success.TButton"
        )
        self.btn_create_bank.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.btn_delete_bank = ttk.Button(
            btn_frame, 
            text="删除存钱罐", 
            command=self.show_delete_dialog,
            style="Danger.TButton"
        )
        self.btn_delete_bank.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def create_content_frame(self):
        """创建内容框架"""
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 创建标签页
        self.notebook = ttk.Notebook(self.content_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 创建各个标签页
        self.create_welcome_tab()
        self.create_bank_tab()
        self.create_transaction_tab()
        self.create_target_tab()
        self.create_history_tab()
        self.create_settings_tab()
        
        # 默认显示欢迎页
        self.notebook.select(0)

    def create_welcome_tab(self):
        """创建欢迎页面"""
        tab = ttk.Frame(self.notebook, padding=30)
        self.notebook.add(tab, text="首页")
        
        # 主容器
        container = ttk.Frame(tab)
        container.pack(fill=tk.BOTH, expand=True)
        
        # 欢迎卡片
        welcome_card = ttk.LabelFrame(
            container, 
            style="Card.TFrame",
            padding=40
        )
        welcome_card.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title = ttk.Label(
            welcome_card, 
            text="白云信用社", 
            font=("Arial", 30),
            foreground="#4a7abc"
        )
        title.pack(pady=(10, 5))
        
        # 版本信息
        version = ttk.Label(
            welcome_card, 
            text="版本 5.6.2", 
            style="Subtitle.TLabel",
            foreground="#718096"
        )
        version.pack(pady=(0, 30))
        
        # 欢迎文本
        welcome_text = ttk.Label(
            welcome_card, 
            text="欢迎使用「白云信用社」", 
            font=("Arial", 18), 
            foreground="#2d3748"
        )
        welcome_text.pack(pady=(0, 40))
        
        # 分隔线
        separator = ttk.Separator(welcome_card, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, pady=20, padx=50)
        
        # 提示信息
        tips = [
            "请从左侧选择或创建一个存钱罐开始",
            "您可以在设置中管理激励语和扩展包",
            "定期备份数据以防止意外丢失",
            "初次使用请到设置调整缩放比例",
            "本程序严格遵守《白云社区用户隐私条约》《白云信用社存储规范》",
            "BaiyunStudio"
        ]
        
        for tip in tips:
            tip_label = ttk.Label(
                welcome_card, 
                text=f"-{tip}-", 
                font=("Arial", 12), 
                foreground="#4a5568"
            )
            tip_label.pack(pady=5)

    def create_bank_tab(self):
        """创建存钱罐信息页面"""
        self.bank_tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.bank_tab, text="存钱罐信息")
        
        # 存钱罐信息标题
        title_frame = ttk.Frame(self.bank_tab)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title = ttk.Label(
            title_frame, 
            text="存钱罐信息", 
            style="Title.TLabel"
        )
        title.pack(side=tk.LEFT)
        
        # 信息展示卡片
        info_frame = ttk.LabelFrame(
            self.bank_tab, 
            padding=20,
            style="Card.TFrame"
        )
        info_frame.pack(fill=tk.X, pady=5)
        
        # 信息项样式
        info_style = {"font": ("Arial", 11), "anchor": tk.W, "width": 12}
        value_style = {"font": ("Arial", 12, "bold"), "anchor": tk.W}
        
        # 创建标签 - 存钱罐名称
        self.bank_name_label = self.create_info_row(info_frame, "当前存钱罐:", "", **info_style)
        
        # 目标信息
        self.target_label = self.create_info_row(info_frame, "储蓄目标:", "¥0.00", **info_style)
        
        # 当前余额
        self.balance_label = self.create_info_row(info_frame, "当前余额:", "¥0.00", **info_style)
        
        # 分隔线
        separator = ttk.Separator(info_frame, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, pady=15)
        
        # 进度条
        progress_frame = ttk.Frame(info_frame)
        progress_frame.pack(fill=tk.X, pady=15)
        self.progress_label = ttk.Label(
            progress_frame, 
            text="进度: 0%", 
            font=("Arial", 10),
            foreground="#4a5568"
        )
        self.progress_label.pack(side=tk.LEFT)
        
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            orient=tk.HORIZONTAL, 
            length=300, 
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, padx=10, expand=True)
        
        # 分隔线
        separator = ttk.Separator(info_frame, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, pady=15)
        
        # 统计信息
        stats_frame = ttk.Frame(info_frame)
        stats_frame.pack(fill=tk.X, pady=15)
        
        self.deposit_count_label = self.create_stat_row(stats_frame, "存款次数:", "0", padx=0)
        self.deposit_days_label = self.create_stat_row(stats_frame, "存款天数:", "0", padx=20)
        
        # 操作按钮
        self.create_action_buttons(self.bank_tab)

    def create_info_row(self, parent, label_text, value_text, **kwargs):
        """创建信息行"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=8)
        
        label = ttk.Label(frame, text=label_text, **kwargs)
        label.pack(side=tk.LEFT)
        
        label_var = ttk.Label(frame, text=value_text, **kwargs)
        label_var.pack(side=tk.LEFT, padx=10)
        return label_var
    
    def create_stat_row(self, parent, label_text, value_text, padx=0):
        """创建统计行"""
        ttk.Label(
            parent, 
            text=label_text, 
            font=("Arial", 10),
            foreground="#4a5568"
        ).pack(side=tk.LEFT, padx=(padx, 0))
        
        label_var = ttk.Label(
            parent, 
            text=value_text, 
            font=("Arial", 10, "bold"),
            foreground="#2d3748"
        )
        label_var.pack(side=tk.LEFT, padx=5)
        return label_var
    
    def create_action_buttons(self, parent):
        """创建操作按钮"""
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=20)
        
        actions = [
            ("存款", self.deposit, "Success.TButton"),
            ("取款", self.withdraw, "Secondary.TButton"),
            ("目标管理", self.show_target_tab, "Primary.TButton"),
            ("查看历史", self.show_history_tab, "Secondary.TButton")
        ]
        
        for text, command, style_name in actions:
            btn = ttk.Button(
                btn_frame, 
                text=text, 
                command=command,
                style=style_name
            )
            btn.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

    def create_transaction_tab(self):
        """创建存取款页面"""
        self.transaction_tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.transaction_tab, text="存取款")
        
        # 标题
        title = ttk.Label(
            self.transaction_tab, 
            text="存取款操作", 
            style="Title.TLabel"
        )
        title.pack(pady=(0, 20))
        
        # 操作面板卡片
        panel = ttk.LabelFrame(
            self.transaction_tab, 
            padding=20,
            style="Card.TFrame"
        )
        panel.pack(fill=tk.X, pady=5)
        
        # 当前余额
        self.current_balance_label = self.create_info_row(panel, "当前余额:", "¥0.00", 
                           font=("Arial", 12), anchor=tk.W)
        
        # 目标余额
        self.target_amount_label = self.create_info_row(panel, "目标金额:", "¥0.00", 
                           font=("Arial", 12), anchor=tk.W)
        
        # 分隔线
        separator = ttk.Separator(panel, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, pady=15)
        
        # 金额输入
        amount_frame = ttk.Frame(panel)
        amount_frame.pack(fill=tk.X, pady=15)
        ttk.Label(
            amount_frame, 
            text="金额:", 
            font=("Arial", 12)
        ).pack(side=tk.LEFT)
        
        self.amount_input = ttk.Entry(
            amount_frame,
            font=("Arial", 12)
        )
        self.amount_input.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # 分隔线
        separator = ttk.Separator(panel, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, pady=15)
        
        # 操作按钮
        btn_frame = ttk.Frame(panel)
        btn_frame.pack(fill=tk.X, pady=15)
        
        self.btn_deposit = ttk.Button(
            btn_frame, 
            text="存款", 
            command=self.deposit,
            style="Success.TButton"
        )
        self.btn_deposit.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        self.btn_withdraw = ttk.Button(
            btn_frame, 
            text="取款", 
            command=self.withdraw,
            style="Secondary.TButton"
        )
        self.btn_withdraw.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # 激励语区域
        self.transaction_encouragement = ttk.Label(
            self.transaction_tab, 
            text="", 
            font=("Arial", 12),
            wraplength=500,
            justify=tk.CENTER,
            foreground="#4a5568",
            background="#f5f7fa"
        )
        self.transaction_encouragement.pack(fill=tk.X, padx=20, pady=20)

    def create_target_tab(self):
        """创建目标管理页面"""
        self.target_tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.target_tab, text="目标管理")
        
        # 标题
        title = ttk.Label(
            self.target_tab, 
            text="目标管理", 
            style="Title.TLabel"
        )
        title.pack(pady=(0, 20))
        
        # 目标设置面板卡片
        panel = ttk.LabelFrame(
            self.target_tab, 
            padding=20,
            style="Card.TFrame"
        )
        panel.pack(fill=tk.X, pady=5)
        
        # 当前目标
        info_style = {"font": ("Arial", 12), "anchor": tk.W}
        self.current_target_label = self.create_info_row(panel, "当前目标:", "¥0.00", **info_style)
        
        # 分隔线
        separator = ttk.Separator(panel, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, pady=15)
        
        # 新目标设置
        new_target_frame = ttk.Frame(panel)
        new_target_frame.pack(fill=tk.X, pady=15)
        ttk.Label(
            new_target_frame, 
            text="新目标:", 
            font=("Arial", 12)
        ).pack(side=tk.LEFT)
        
        self.new_target_input = ttk.Entry(
            new_target_frame,
            font=("Arial", 12)
        )
        self.new_target_input.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        btn_set_target = ttk.Button(
            new_target_frame, 
            text="设置目标", 
            command=self.set_new_target,
            style="Primary.TButton"
        )
        btn_set_target.pack(side=tk.LEFT, padx=5)
        
        # 分隔线
        separator = ttk.Separator(panel, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, pady=15)
        
        # 模式选择
        mode_frame = ttk.Frame(panel)
        mode_frame.pack(fill=tk.X, pady=15)
        ttk.Label(
            mode_frame, 
            text="储蓄模式:", 
            font=("Arial", 12)
        ).pack(side=tk.LEFT)
        
        self.mode_var = tk.StringVar()
        self.mode_combo = ttk.Combobox(
            mode_frame, 
            textvariable=self.mode_var, 
            state="readonly",
            width=18,
            font=("Arial", 12)
        )
        self.mode_combo['values'] = ("累积存钱模式", "单目标存钱模式")
        self.mode_combo.current(0)
        self.mode_combo.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        btn_set_mode = ttk.Button(
            mode_frame, 
            text="应用模式", 
            command=self.set_saving_mode,
            style="Primary.TButton"
        )
        btn_set_mode.pack(side=tk.LEFT, padx=5)
        
        # 分隔线
        separator = ttk.Separator(panel, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, pady=15)
        
        # 重置按钮
        btn_reset = ttk.Button(
            panel, 
            text="重置进度", 
            command=self.reset_progress,
            style="Danger.TButton"
        )
        btn_reset.pack(pady=15, fill=tk.X)
        
        # 进度信息卡片
        progress_group = ttk.LabelFrame(
            self.target_tab, 
            padding=20,
            style="Card.TFrame"
        )
        progress_group.pack(fill=tk.X, pady=10)
        
        # 进度条
        self.target_progress_label = ttk.Label(
            progress_group, 
            text="进度: 0%", 
            font=("Arial", 10),
            foreground="#4a5568"
        )
        self.target_progress_label.pack(pady=5)
        
        self.target_progress_bar = ttk.Progressbar(
            progress_group, 
            orient=tk.HORIZONTAL, 
            length=300, 
            mode='determinate'
        )
        self.target_progress_bar.pack(fill=tk.X, padx=10, pady=5)
        
        # 分隔线
        separator = ttk.Separator(progress_group, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, pady=15)
        
        # 剩余金额
        remaining_frame = ttk.Frame(progress_group)
        remaining_frame.pack(fill=tk.X, pady=10)
        ttk.Label(
            remaining_frame, 
            text="剩余金额:", 
            font=("Arial", 12)
        ).pack(side=tk.LEFT)
        self.remaining_amount_label = ttk.Label(
            remaining_frame, 
            text="¥0.00", 
            font=("Arial", 12, "bold")
        )
        self.remaining_amount_label.pack(side=tk.LEFT, padx=10)

    def create_history_tab(self):
        """创建历史记录页面"""
        self.history_tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.history_tab, text="历史记录")
        
        # 标题
        title = ttk.Label(
            self.history_tab, 
            text="存取款历史记录", 
            style="Title.TLabel"
        )
        title.pack(pady=(0, 20))
        
        # 控制栏卡片
        control_frame = ttk.LabelFrame(
            self.history_tab, 
            padding=15,
            style="Card.TFrame"
        )
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 时间格式选择
        format_frame = ttk.Frame(control_frame)
        format_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(
            format_frame, 
            text="时间格式:", 
            font=("Arial", 10)
        ).pack(side=tk.LEFT)
        
        self.time_format_var = tk.StringVar()
        self.time_format_combo = ttk.Combobox(
            format_frame, 
            textvariable=self.time_format_var, 
            state="readonly",
            width=25, 
            font=("Arial", 10)
        )
        self.time_format_combo['values'] = (
            "仅日期",
            "精确到小时",
            "精确到分钟",
            "精确到秒"
        )
        self.time_format_combo.current(3)
        self.time_format_combo.pack(side=tk.LEFT, padx=5)
        self.time_format_combo.bind("<<ComboboxSelected>>", lambda e: self.update_history_display())
        
        # 显示模式选择
        display_frame = ttk.Frame(control_frame)
        display_frame.pack(side=tk.LEFT, padx=10)
        ttk.Label(
            display_frame, 
            text="显示模式:", 
            font=("Arial", 10)
        ).pack(side=tk.LEFT)
        
        self.display_mode_var = tk.StringVar()
        self.display_mode_combo = ttk.Combobox(
            display_frame, 
            textvariable=self.display_mode_var, 
            state="readonly",
            width=15, 
            font=("Arial", 10)
        )
        self.display_mode_combo['values'] = ("显示所有记录", "按月显示记录")
        self.display_mode_combo.current(0)
        self.display_mode_combo.pack(side=tk.LEFT, padx=5)
        self.display_mode_combo.bind("<<ComboboxSelected>>", lambda e: self.toggle_month_combo())
        
        # 月份选择（初始隐藏）
        self.month_frame = ttk.Frame(control_frame)
        self.month_frame.pack(side=tk.LEFT, padx=10)
        ttk.Label(
            self.month_frame, 
            text="选择月份:", 
            font=("Arial", 10)
        ).pack(side=tk.LEFT)
        
        self.month_var = tk.StringVar()
        self.month_combo = ttk.Combobox(
            self.month_frame, 
            textvariable=self.month_var, 
            state="readonly",
            width=12, 
            font=("Arial", 10)
        )
        self.month_combo.pack(side=tk.LEFT, padx=5)
        self.month_combo.bind("<<ComboboxSelected>>", lambda e: self.update_history_display())
        self.month_frame.pack_forget()
        
        # 刷新按钮
        btn_refresh = ttk.Button(
            control_frame, 
            text="刷新", 
            command=self.update_history_display,
            style="Primary.TButton"
        )
        btn_refresh.pack(side=tk.RIGHT, padx=5)
        
        # 历史记录表格卡片
        table_frame = ttk.Frame(self.history_tab, style="Card.TFrame")
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))
        
        # 历史记录表格
        columns = ("序号", "日期时间", "金额", "剩余目标")
        self.history_tree = ttk.Treeview(
            table_frame, 
            columns=columns, 
            show="headings",
            height=15
        )
        
        # 设置列宽
        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=120, anchor=tk.CENTER)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def create_settings_tab(self):
        """创建设置页面"""
        self.settings_tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.settings_tab, text="系统设置")
        
        # 标题
        title = ttk.Label(
            self.settings_tab, 
            text="系统设置", 
            style="Title.TLabel"
        )
        title.pack(pady=(0, 20))
        
        # 设置选项卡
        self.settings_notebook = ttk.Notebook(self.settings_tab)
        self.settings_notebook.pack(fill=tk.BOTH, expand=True)
        
        # 通用设置标签页
        self.create_general_settings_tab()
        
        # 激励语设置标签页
        self.create_encouragement_settings_tab()
        
        # 扩展包管理标签页
        self.create_pack_management_tab()

    def create_general_settings_tab(self):
        """创建通用设置标签页"""
        tab = ttk.Frame(self.settings_notebook, padding=10)
        self.settings_notebook.add(tab, text="通用设置")
        
        # 自动打开设置卡片
        auto_open_frame = ttk.LabelFrame(
            tab, 
            padding=15,
            style="Card.TFrame"
        )
        auto_open_frame.pack(fill=tk.X, pady=5)
        
        self.auto_open_check = ttk.Checkbutton(
            auto_open_frame, 
            text="启动时自动打开上一次使用的存钱罐",
            variable=self.auto_open_var,
            command=self.toggle_auto_open
        )
        self.auto_open_check.pack(padx=5, pady=5, anchor=tk.W)
        
        self.last_bank_label = ttk.Label(
            auto_open_frame, 
            text="上一次打开的存钱罐: 无"
        )
        self.last_bank_label.pack(padx=5, pady=5, anchor=tk.W)
        
        # 分隔线
        separator = ttk.Separator(auto_open_frame, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, pady=10)
        
        # 缩放比例设置
        zoom_frame = ttk.Frame(auto_open_frame)
        zoom_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Label(
            zoom_frame, 
            text="缩放比例:", 
            font=("Arial", 10)
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        self.zoom_factor_var = tk.DoubleVar(value=self.zoom_factor)
        zoom_scale = ttk.Scale(
            zoom_frame,
            from_=1.4,
            to=3.0,
            variable=self.zoom_factor_var,
            length=200,
            command=self.on_zoom_change
        )
        zoom_scale.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 显示当前缩放值
        self.zoom_value_label = ttk.Label(
            zoom_frame, 
            text=f"{self.zoom_factor_var.get():.1f}x"
        )
        self.zoom_value_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 字体大小设置
        font_frame = ttk.Frame(auto_open_frame)
        font_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Label(
            font_frame, 
            text="基础字体大小:", 
            font=("Arial", 10)
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        self.font_size_var = tk.IntVar(value=self.base_font_size)
        font_sizes = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 18]
        font_combo = ttk.Combobox(
            font_frame, 
            textvariable=self.font_size_var, 
            values=font_sizes, 
            state="readonly",
            width=13
        )
        font_combo.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 应用按钮
        apply_frame = ttk.Frame(auto_open_frame)
        apply_frame.pack(fill=tk.X, padx=5, pady=10)
        
        btn_apply = ttk.Button(
            apply_frame, 
            text="应用缩放和字体设置", 
            command=self.apply_zoom_and_font,
            style="Primary.TButton",
            width=15
        )
        btn_apply.pack(pady=10, padx=10, side=tk.RIGHT)
        
        # 分隔线
        separator = ttk.Separator(auto_open_frame, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, pady=10)
        
        # 历史记录设置卡片
        history_frame = ttk.Frame(auto_open_frame)
        history_frame.pack(fill=tk.X, padx=5, pady=10)
        
        # 时间格式设置
        time_format_frame = ttk.Frame(history_frame)
        time_format_frame.pack(fill=tk.X, padx=5, pady=8)
        ttk.Label(
            time_format_frame, 
            text="时间格式:", 
            font=("Arial", 10)
        ).pack(side=tk.LEFT)
        
        self.history_time_format_var = tk.StringVar()
        self.history_time_combo = ttk.Combobox(
            time_format_frame, 
            textvariable=self.history_time_format_var, 
            state="readonly",
            width=25
        )
        self.history_time_combo['values'] = (
            "仅日期",
            "精确到小时",
            "精确到分钟",
            "精确到秒"
        )
        self.history_time_combo.pack(side=tk.LEFT, padx=10)
        
        # 显示模式设置
        display_mode_frame = ttk.Frame(history_frame)
        display_mode_frame.pack(fill=tk.X, padx=5, pady=8)
        ttk.Label(
            display_mode_frame, 
            text="显示模式:", 
            font=("Arial", 10)
        ).pack(side=tk.LEFT)
        
        self.history_display_var = tk.StringVar()
        self.history_display_combo = ttk.Combobox(
            display_mode_frame, 
            textvariable=self.history_display_var, 
            state="readonly",
            width=15
        )
        self.history_display_combo['values'] = ("显示所有记录", "按月显示记录")
        self.history_display_combo.pack(side=tk.LEFT, padx=10)
        
        # 应用按钮
        btn_apply_history = ttk.Button(
            history_frame, 
            text="应用设置", 
            command=self.apply_history_settings,
            style="Primary.TButton",
            width=10
        )
        btn_apply_history.pack(pady=10, padx=10, side=tk.RIGHT)
        
        # 分隔线
        separator = ttk.Separator(auto_open_frame, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, pady=10)
        
        # 数据备份卡片
        backup_frame = ttk.Frame(auto_open_frame)
        backup_frame.pack(fill=tk.X, padx=5, pady=10)
        
        btn_backup = ttk.Button(
            backup_frame, 
            text="立即备份当前存钱罐", 
            command=self.create_backup,
            style="Primary.TButton"
        )
        btn_backup.pack(padx=5, pady=5, fill=tk.X)
        
        btn_restore = ttk.Button(
            backup_frame, 
            text="恢复备份", 
            command=self.show_restore_backup,
            style="Secondary.TButton"
        )
        btn_restore.pack(padx=5, pady=5, fill=tk.X)

    def create_encouragement_settings_tab(self):
        """创建激励语设置标签页"""
        tab = ttk.Frame(self.settings_notebook, padding=10)
        self.settings_notebook.add(tab, text="激励语设置")
        
        # 激励语设置卡片
        encouragement_frame = ttk.LabelFrame(
            tab, 
            padding=15,
            style="Card.TFrame"
        )
        encouragement_frame.pack(fill=tk.BOTH, expand=True)
        
        # 激励语列表
        self.encouragement_list = tk.Listbox(
            encouragement_frame, 
            height=10,
            borderwidth=0,
            highlightthickness=0,
            bg="#ffffff",
            font=("Arial", 10)
        )
        scrollbar = ttk.Scrollbar(encouragement_frame, orient=tk.VERTICAL, command=self.encouragement_list.yview)
        self.encouragement_list.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.encouragement_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 按钮框架
        btn_frame = ttk.Frame(encouragement_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        btn_add_enc = ttk.Button(
            btn_frame, 
            text="添加激励语", 
            command=self.add_encouragement,
            style="Success.TButton"
        )
        btn_add_enc.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        btn_remove_enc = ttk.Button(
            btn_frame, 
            text="删除激励语", 
            command=self.remove_encouragement,
            style="Danger.TButton"
        )
        btn_remove_enc.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 更新激励语列表
        self.update_encouragement_list()

    def create_pack_management_tab(self):
        """创建扩展包管理标签页"""
        tab = ttk.Frame(self.settings_notebook, padding=10)
        self.settings_notebook.add(tab, text="扩展包管理")
        
        # 扩展包管理卡片
        pack_frame = ttk.LabelFrame(
            tab, 
            padding=15,
            style="Card.TFrame"
        )
        pack_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 扩展包列表
        self.pack_list = tk.Listbox(
            pack_frame, 
            height=8,
            borderwidth=0,
            highlightthickness=0,
            bg="#ffffff",
            font=("Arial", 10)
        )
        scrollbar = ttk.Scrollbar(pack_frame, orient=tk.VERTICAL, command=self.pack_list.yview)
        self.pack_list.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.pack_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 更新扩展包列表
        self.update_pack_list()
        
        # 按钮框架
        btn_frame = ttk.Frame(pack_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        btn_import = ttk.Button(
            btn_frame, 
            text="导入选中包", 
            command=self.import_selected_pack,
            style="Primary.TButton"
        )
        btn_import.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        btn_view = ttk.Button(
            btn_frame, 
            text="查看内容", 
            command=self.view_pack_content,
            style="Secondary.TButton"
        )
        btn_view.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        btn_delete = ttk.Button(
            btn_frame, 
            text="删除包", 
            command=self.delete_pack,
            style="Danger.TButton"
        )
        btn_delete.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        btn_scan = ttk.Button(
            btn_frame, 
            text="扫描扩展包", 
            command=self.scan_for_packs,
            style="Secondary.TButton"
        )
        btn_scan.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

    def update_encouragement(self):
        """更新激励语"""
        encouragement = get_random_encouragement()
        self.transaction_encouragement.config(text=f'{encouragement}')
        self.status_label.config(text=f"激励语: {encouragement}")
        self.root.after(15000, self.update_encouragement)

    def update_bank_list(self):
        """更新存钱罐列表"""
        self.bank_list.delete(0, tk.END)
        banks = list_piggy_banks()
        for bank in banks:
            self.bank_list.insert(tk.END, bank)

    def check_auto_open(self):
        """检查自动打开设置"""
        settings = load_global_settings()
        self.auto_open_var.set(settings["auto_open_last_bank"])
        
        last_bank = settings.get("last_opened_bank", "")
        if last_bank:
            self.last_bank_label.config(text=f"上一次打开的存钱罐: {last_bank}")
        
        if settings["auto_open_last_bank"] and last_bank:
            banks = list_piggy_banks()
            if last_bank in banks:
                self.select_bank_by_name(last_bank)
                return
        
        self.notebook.select(0)

    def select_bank_by_name(self, bank_name):
        """根据名称选择存钱罐"""
        banks = self.bank_list.get(0, tk.END)
        if bank_name in banks:
            index = banks.index(bank_name)
            self.bank_list.selection_clear(0, tk.END)
            self.bank_list.selection_set(index)
            self.bank_list.see(index)
            self.bank_list.event_generate("<<ListboxSelect>>")

    def on_bank_selected(self, event):
        """处理存钱罐选择事件"""
        selected = self.bank_list.curselection()
        if not selected:
            return
            
        bank_name = self.bank_list.get(selected[0])
        self.current_bank = bank_name
        self.bank_data = load_data(bank_name)
        
        update_last_opened_bank(bank_name)
        self.update_bank_info()
        self.update_transaction_info()
        self.update_target_info()
        self.update_history_display()
        self.notebook.select(1)
        self.status_label.config(text=f"已选择存钱罐: {bank_name}")

    def update_bank_info(self):
        """更新存钱罐信息"""
        if not self.current_bank or not self.bank_data:
            return
        
        self.bank_name_label.config(text=self.current_bank)
        self.target_label.config(text=f"¥{self.bank_data['target']:.2f}")
        self.balance_label.config(text=f"¥{self.bank_data['current_saved']:.2f}")
        self.deposit_count_label.config(text=str(self.bank_data['total_deposits']))
        self.deposit_days_label.config(text=str(len(self.bank_data['deposit_dates'])))
        
        # 更新进度
        target = self.bank_data['target']
        saved = self.bank_data['current_saved']
        if target > 0:
            progress = min(100, int(saved / target * 100))
            self.progress_bar['value'] = progress
            self.progress_label.config(text=f"进度: {progress}%")
        else:
            self.progress_bar['value'] = 0
            self.progress_label.config(text="未设置目标")

    def update_transaction_info(self):
        """更新存取款信息"""
        if not self.current_bank or not self.bank_data:
            return
        
        self.current_balance_label.config(text=f"¥{self.bank_data['current_saved']:.2f}")
        self.target_amount_label.config(text=f"¥{self.bank_data['target']:.2f}")
        self.amount_input.delete(0, tk.END)

    def update_target_info(self):
        """更新目标管理信息"""
        if not self.current_bank or not self.bank_data:
            return
        
        self.current_target_label.config(text=f"¥{self.bank_data['target']:.2f}")
        
        # 设置模式
        if self.bank_data['saving_mode'] == SavingMode.ACCUMULATE.value:
            self.mode_combo.current(0)
        else:
            self.mode_combo.current(1)
        
        # 更新进度
        target = self.bank_data['target']
        saved = self.bank_data['current_saved']
        remaining = max(target - saved, 0)
        
        self.remaining_amount_label.config(text=f"¥{remaining:.2f}")
        
        if target > 0:
            progress = min(100, int(saved / target * 100))
            self.target_progress_bar['value'] = progress
            self.target_progress_label.config(text=f"进度: {progress}%")
        else:
            self.target_progress_bar['value'] = 0
            self.target_progress_label.config(text="未设置目标")

    def toggle_month_combo(self):
        """切换月份选择框显示状态"""
        if self.display_mode_combo.current() == 1:  # 按月显示
            if self.current_bank and self.bank_data:
                months = set()
                for date_str in self.bank_data['deposit_dates']:
                    year_month = date_str.split('-')
                    if len(year_month) >= 2:
                        year_month = '-'.join(year_month[:2])
                        months.add(year_month)
                months = sorted(months, reverse=True)
                self.month_combo['values'] = months
                if months:
                    self.month_combo.current(0)
                self.month_frame.pack(side=tk.LEFT, padx=10)
            else:
                self.month_frame.pack_forget()
        else:
            self.month_frame.pack_forget()
        self.update_history_display()

    def update_history_display(self):
        """更新历史记录显示"""
        if not self.current_bank or not self.bank_data:
            return
    
        # 清除现有数据
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)
    
        history = self.bank_data['deposit_history']
    
        if not history:
            return
    
        # 格式化时间
        time_format_map = {
            0: "date",  # 仅日期
            1: "hour",  # 精确到小时
            2: "minute",  # 精确到分钟
            3: "second"  # 精确到秒
        }
        time_format = time_format_map.get(self.time_format_combo.current(), "second")
    
        # 显示模式
        display_mode = "all" if self.display_mode_combo.current() == 0 else "monthly"
    
        # 按日期排序
        try:
            history = sorted(
                history,
                key=lambda x: datetime.strptime(x["date"].split()[0], DATE_FORMAT),
                reverse=True
            )
        except (ValueError, KeyError):
            history = history[::-1]  # 简单反转作为后备
    
        # 如果是按月显示，只显示选定月份
        if display_mode == "monthly":
            selected_month = self.month_var.get()
            if selected_month:
                history = [record for record in history 
                          if record["date"].split()[0].startswith(selected_month)]
            else:
                current_month = datetime.now().strftime("%Y-%m")
                history = [record for record in history 
                          if record["date"].split()[0].startswith(current_month)]
    
        # 填充表格
        for idx, record in enumerate(history):
            date_str = record["date"]
            dt = None
            try:
                for fmt in [DATETIME_FORMAT, DATE_FORMAT, "%Y-%m-%d %H:%M:%S"]:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    formatted_date = date_str
                
                if dt:
                    formats = {
                        "date": "%Y-%m-%d",
                        "hour": "%Y-%m-%d %H时",
                        "minute": "%Y-%m-%d %H:%M",
                        "second": "%Y-%m-%d %H:%M:%S"
                    }
                    formatted_date = dt.strftime(formats.get(time_format, "%Y-%m-%d %H:%M:%S"))
                else:
                    formatted_date = date_str
            except ValueError:
                formatted_date = date_str
    
            amount = record['amount']
            amount_str = f"+{amount:.2f}" if amount >= 0 else f"{amount:.2f}"
    
            remaining = record.get('remaining', 0)
    
            self.history_tree.insert("", tk.END, values=(
                len(history) - idx,
                formatted_date,
                amount_str,
                f"¥{remaining:.2f}"
            ))

    def create_new_bank(self):
        """创建新存钱罐"""
        create_window = tk.Toplevel(self.root)
        create_window.title("创建存钱罐")
        create_window.geometry("630x1570")
        create_window.resizable(False, False)
        create_window.transient(self.root)
        create_window.grab_set()
        
        # 添加全屏按钮
        self.add_fullscreen_button(create_window)
        
        # 主框架
        main_frame = ttk.Frame(create_window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title = ttk.Label(
            main_frame, 
            text="创建新存钱罐", 
            font=("Arial", 14)
        )
        title.pack(pady=(0, 15))
        
        # 输入框框架
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=5)
        
        # 输入框
        ttk.Label(
            input_frame, 
            text="存钱罐名称:", 
            font=("Arial", 12)
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        name_entry = ttk.Entry(
            input_frame,
            font=("Arial", 12)
        )
        name_entry.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        # 显示虚拟键盘
        keyboard_frame = ttk.Frame(main_frame)
        keyboard_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        keyboard = VirtualKeyboard(keyboard_frame, name_entry, input_type="text")
        keyboard.show()
        
        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        def create():
            bank_name = name_entry.get().strip()
            if not bank_name:
                messagebox.showwarning("名称错误", "请输入存钱罐名称！")
                return
                
            if re.search(r'[\\/*?:"<>|]', bank_name):
                messagebox.showwarning("名称错误", "名称包含非法字符！")
                return
                
            result = create_piggy_bank(bank_name)
            if result:
                self.update_bank_list()
                self.select_bank_by_name(bank_name)
                messagebox.showinfo("创建成功", f"存钱罐 '{bank_name}' 创建成功！")
                create_window.destroy()
            else:
                messagebox.showerror("创建失败", "无法创建存钱罐，名称可能已存在！")
        
        create_btn = ttk.Button(
            btn_frame, 
            text="创建", 
            command=create,
            style="Success.TButton",
            width=15
        )
        create_btn.pack(side=tk.LEFT, padx=15)
        
        cancel_btn = ttk.Button(
            btn_frame, 
            text="取消", 
            command=create_window.destroy,
            style="Secondary.TButton",
            width=15
        )
        cancel_btn.pack(side=tk.LEFT, padx=15)

    def show_delete_dialog(self):
        """显示删除存钱罐对话框"""
        delete_window = tk.Toplevel(self.root)
        delete_window.title("删除存钱罐")
        delete_window.geometry("630x1570")
        delete_window.resizable(False, False)
        delete_window.transient(self.root)
        delete_window.grab_set()
        
        # 添加全屏按钮
        self.add_fullscreen_button(delete_window)
        
        # 主框架
        main_frame = ttk.Frame(delete_window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title = ttk.Label(
            main_frame, 
            text="选择要删除的存钱罐", 
            font=("Arial", 14)
        )
        title.pack(pady=(0, 15))
        
        # 提示
        info_label = ttk.Label(
            main_frame,
            text="请谨慎删除,删除后无法恢复"
        )
        info_label.pack(pady=(0, 10))
        
        # 存钱罐列表框架
        list_frame = ttk.LabelFrame(
            main_frame, 
            padding=15,
            style="Card.TFrame"
        )
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 存钱罐列表（多选）
        bank_list = tk.Listbox(
            list_frame, 
            selectmode=tk.EXTENDED,
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=bank_list.yview)
        bank_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 填充存钱罐
        banks = list_piggy_banks()
        for bank in banks:
            bank_list.insert(tk.END, bank)
        
        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        def delete_selected():
            selected_indices = bank_list.curselection()
            if not selected_indices:
                messagebox.showwarning("警告", "请至少选择一个存钱罐！")
                return
                
            selected_banks = [bank_list.get(i) for i in selected_indices]
            
            confirm_msg = f"确定要删除以下 {len(selected_banks)} 个存钱罐吗？此操作不可逆！\n\n"
            confirm_msg += "\n".join([f"• {bank}" for bank in selected_banks])
            
            if not messagebox.askyesno("确认删除", confirm_msg):
                return
                
            success = []
            failed = []
            current_deleted = False
            
            for bank_name in selected_banks:
                try:
                    shutil.rmtree(MAIN_DATA_DIR / bank_name)
                    
                    if self.current_bank == bank_name:
                        current_deleted = True
                    
                    settings = load_global_settings()
                    if settings["last_opened_bank"] == bank_name:
                        settings["last_opened_bank"] = None
                        save_global_settings(settings)
                    
                    success.append(bank_name)
                except Exception as e:
                    failed.append((bank_name, str(e)))
            
            self.update_bank_list()
            
            if current_deleted:
                self.current_bank = None
                self.bank_data = None
                self.update_bank_info()
                self.update_transaction_info()
                self.update_target_info()
                self.update_history_display()
                self.notebook.select(0)
            
            result_msg = ""
            if success:
                result_msg += f"成功删除 {len(success)} 个存钱罐！\n"
            if failed:
                result_msg += f"\n删除失败 {len(failed)} 个存钱罐：\n"
                for name, error in failed:
                    result_msg += f"• {name}: {error}\n"
            
            messagebox.showinfo("删除结果", result_msg)
            delete_window.destroy()
        
        delete_btn = ttk.Button(
            btn_frame, 
            text="删除选中", 
            command=delete_selected,
            style="Danger.TButton",
            width=15
        )
        delete_btn.pack(side=tk.LEFT, padx=15)
        
        cancel_btn = ttk.Button(
            btn_frame, 
            text="取消", 
            command=delete_window.destroy,
            style="Secondary.TButton",
            width=15
        )
        cancel_btn.pack(side=tk.LEFT, padx=15)

    def show_transaction_tab(self):
        """显示存取款页面"""
        if not self.current_bank:
            messagebox.showwarning("未选择", "请先选择一个存钱罐！")
            return
        self.notebook.select(2)

    def show_target_tab(self):
        """显示目标管理页面"""
        if not self.current_bank:
            messagebox.showwarning("未选择", "请先选择一个存钱罐！")
            return
        self.notebook.select(3)

    def show_history_tab(self):
        """显示历史记录页面"""
        if not self.current_bank:
            messagebox.showwarning("未选择", "请先选择一个存钱罐！")
            return
        self.notebook.select(4)
        self.update_history_display()

    def deposit(self):
        """存款操作"""
        if not self.current_bank or not self.bank_data:
            messagebox.showwarning("未选择", "请先选择一个存钱罐！")
            return
            
        try:
            amount = float(self.amount_input.get())
            if amount <= 0:
                messagebox.showwarning("金额错误", "存款金额必须大于0！")
                return
        except ValueError:
            messagebox.showwarning("输入错误", "请输入有效的数字！")
            return
            
        target = self.bank_data['target']
        current = self.bank_data['current_saved']
        if target > 0 and current + amount > target:
            remaining = target - current
            messagebox.showwarning("超过目标", f"存款金额超过目标！最多可存 {remaining:.2f}元")
            return
            
        now = datetime.now()
        date_only = now.date().isoformat()
        datetime_full = now.strftime(DATETIME_FORMAT)
        
        new_balance = current + amount
        self.bank_data["current_saved"] = new_balance
        self.bank_data["total_deposits"] += 1
        
        if date_only not in self.bank_data["deposit_dates"]:
            self.bank_data["deposit_dates"].append(date_only)
        
        self.bank_data["deposit_history"].append({
            "date": datetime_full,
            "amount": amount,
            "remaining": target - new_balance
        })
        
        if save_data(self.current_bank, self.bank_data):
            self.update_bank_info()
            self.update_transaction_info()
            self.update_target_info()
            self.update_history_display()
            
            encouragement = get_random_encouragement()
            messagebox.showinfo(
                "存款成功", 
                f"成功存款 {amount:.2f}元！\n\n{encouragement}"
            )
        else:
            messagebox.showerror("保存失败", "无法保存数据，请重试！")

    def withdraw(self):
        """取款操作"""
        if not self.current_bank or not self.bank_data:
            return
            
        try:
            amount = float(self.amount_input.get())
            if amount <= 0:
                messagebox.showwarning("金额错误", "取款金额必须大于0！")
                return
        except ValueError:
            messagebox.showwarning("输入错误", "请输入有效的数字！")
            return
    
        amount = -abs(amount)
        current = self.bank_data['current_saved']
        new_balance = current + amount
    
        if new_balance < 0:
            messagebox.showwarning("余额不足", f"取款金额不能超过当前存款 {current:.2f}元")
            return
    
        now = datetime.now()
        datetime_full = now.strftime(DATETIME_FORMAT)
    
        self.bank_data["current_saved"] = new_balance
    
        remaining = self.bank_data['target'] - new_balance
        self.bank_data["deposit_history"].append({
            "date": datetime_full,
            "amount": amount,
            "remaining": remaining
        })
    
        if save_data(self.current_bank, self.bank_data):
            self.update_bank_info()
            self.update_transaction_info()
            self.update_target_info()
            self.update_history_display()
            
            messagebox.showinfo(
                "取款成功", 
                f"成功取款 {-amount:.2f}元！\n当前余额: ¥{new_balance:.2f}"
            )
        else:
            messagebox.showerror("保存失败", "无法保存数据，请重试！")

    def set_new_target(self):
        """设置新目标"""
        if not self.current_bank or not self.bank_data:
            messagebox.showwarning("未选择", "请先选择一个存钱罐！")
            return
            
        try:
            new_target = float(self.new_target_input.get())
        except ValueError:
            messagebox.showwarning("输入错误", "请输入有效的数字！")
            return
            
        if new_target <= 0:
            messagebox.showwarning("目标错误", "目标金额必须大于0！")
            return
            
        if SavingMode(self.bank_data['saving_mode']) == SavingMode.PER_TARGET:
            self.bank_data = initialize_data()
            self.bank_data['target'] = new_target
            self.bank_data['saving_mode'] = SavingMode.PER_TARGET.value
        else:
            self.bank_data['target'] = new_target
        
        if save_data(self.current_bank, self.bank_data):
            self.update_bank_info()
            self.update_target_info()
            self.update_history_display()
            
            messagebox.showinfo(
                "目标设置成功", 
                f"新目标已设置为 ¥{new_target:.2f}"
            )
        else:
            messagebox.showerror("保存失败", "无法保存数据，请重试！")

    def set_saving_mode(self):
        """设置储蓄模式"""
        if not self.current_bank or not self.bank_data:
            return
            
        new_mode = self.mode_combo.current()
        if new_mode == 0:
            self.bank_data['saving_mode'] = SavingMode.ACCUMULATE.value
        else:
            self.bank_data['saving_mode'] = SavingMode.PER_TARGET.value
        
        if save_data(self.current_bank, self.bank_data):
            messagebox.showinfo(
                "模式设置成功", 
                f"已设置为 {self.mode_combo.get()}"
            )
        else:
            messagebox.showerror("保存失败", "无法保存数据，请重试！")

    def reset_progress(self):
        """重置进度"""
        if not self.current_bank or not self.bank_data:
            return
            
        if messagebox.askyesno("确认重置", "确定要重置当前存钱罐的进度吗？此操作不可恢复！"):
            self.bank_data = initialize_data()
            if save_data(self.current_bank, self.bank_data):
                self.update_bank_info()
                self.update_transaction_info()
                self.update_target_info()
                self.update_history_display()
                messagebox.showinfo("重置成功", "存钱罐进度已重置！")
            else:
                messagebox.showerror("保存失败", "无法保存数据，请重试！")

    def toggle_auto_open(self):
        """切换自动打开设置"""
        settings = load_global_settings()
        settings["auto_open_last_bank"] = self.auto_open_var.get()
        save_global_settings(settings)
        last_bank = settings.get("last_opened_bank", "") or "无"
        self.last_bank_label.config(text=f"上一次打开的存钱罐: {last_bank}")

    def create_backup(self):
        """创建备份"""
        if not self.current_bank or not self.bank_data:
            messagebox.showwarning("未选择", "请先选择一个存钱罐！")
            return
            
        if save_data(self.current_bank, self.bank_data):
            messagebox.showinfo("备份成功", "当前存钱罐数据已成功备份！")
        else:
            messagebox.showerror("备份失败", "无法创建备份，请重试！")

    def show_restore_backup(self):
        """显示恢复备份对话框"""
        if not self.current_bank:
            messagebox.showwarning("未选择", "请先选择一个存钱罐！")
            return
            
        backup_files = list_backup_files(self.current_bank)
        if not backup_files:
            messagebox.showinfo("无备份", "没有找到备份文件")
            return
            
        # 创建选择对话框
        restore_window = tk.Toplevel(self.root)
        restore_window.title("恢复备份")
        restore_window.geometry("630x1750")
        restore_window.resizable(False, False)
        restore_window.transient(self.root)
        restore_window.grab_set()
        
        # 添加全屏按钮
        self.add_fullscreen_button(restore_window)
        
        # 主框架
        main_frame = ttk.Frame(restore_window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(
            restore_window, 
            text="选择要恢复的备份文件", 
            font=("Arial", 12)
        ).pack(pady=15)
        
        frame = ttk.Frame(main_frame, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(
            frame, 
            yscrollcommand=scrollbar.set
        )
        for file in backup_files:
            mtime = datetime.fromtimestamp(os.path.getmtime(file)).strftime("%Y-%m-%d %H:%M:%S")
            listbox.insert(tk.END, f"{file.name} (备份时间: {mtime})")
        listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        
        btn_frame = ttk.Frame(restore_window, padding=10)
        btn_frame.pack(fill=tk.X)
        
        def restore():
            selected = listbox.curselection()
            if not selected:
                messagebox.showwarning("未选择", "请选择一个备份文件")
                return
                
            backup_file = backup_files[selected[0]]
            if restore_backup_file(self.current_bank, backup_file):
                self.bank_data = load_data(self.current_bank)
                self.update_bank_info()
                self.update_transaction_info()
                self.update_target_info()
                self.update_history_display()
                restore_window.destroy()
                messagebox.showinfo("恢复成功", "备份已成功恢复！")
            else:
                messagebox.showerror("恢复失败", "无法恢复备份，请重试")
        
        ttk.Button(
            btn_frame, 
            text="恢复选中备份", 
            command=restore,
            style="Primary.TButton",
            width=15
        ).pack(side=tk.LEFT, padx=15)
        
        ttk.Button(
            btn_frame, 
            text="取消", 
            command=restore_window.destroy,
            style="Secondary.TButton",
            width=15
        ).pack(side=tk.LEFT, padx=15)

    def add_encouragement(self):
        """添加激励语"""
        text = simpledialog.askstring("添加激励语", "请输入激励语内容:")
        if text:
            default, custom = load_encouragements()
            custom.append(text)
            if save_custom_encouragements(custom):
                self.update_encouragement_list()
                messagebox.showinfo("添加成功", "激励语已添加！")
            else:
                messagebox.showerror("保存失败", "无法保存激励语，请重试！")

    def remove_encouragement(self):
        """删除激励语"""
        selected = self.encouragement_list.curselection()
        if not selected:
            messagebox.showwarning("未选择", "请先选择一条激励语！")
            return
            
        text = self.encouragement_list.get(selected[0])
        if messagebox.askyesno("确认删除", f"确定要删除激励语 '{text}' 吗？"):
            default, custom = load_encouragements()
            if text in custom:
                custom.remove(text)
                if save_custom_encouragements(custom):
                    self.update_encouragement_list()
                    messagebox.showinfo("删除成功", "激励语已删除！")
                else:
                    messagebox.showerror("保存失败", "无法保存激励语，请重试！")

    def update_encouragement_list(self):
        """更新激励语列表"""
        self.encouragement_list.delete(0, tk.END)
        _, custom = load_encouragements()
        for text in custom:
            self.encouragement_list.insert(tk.END, text)

    def update_pack_list(self):
        """更新扩展包列表"""
        self.pack_list.delete(0, tk.END)
        packs = list_encouragement_packs()
        for pack in packs:
            self.pack_list.insert(tk.END, pack)

    def import_selected_pack(self):
        """导入选中的扩展包"""
        selected = self.pack_list.curselection()
        if not selected:
            messagebox.showwarning("未选择", "请先选择一个扩展包！")
            return
            
        pack_name = self.pack_list.get(selected[0])
        pack_path = ENCOURAGEMENT_PACK_DIR / f"{pack_name}.hl"
        
        if import_encouragement_pack(pack_path):
            self.update_encouragement_list()
            messagebox.showinfo("导入成功", f"成功导入扩展包: {pack_name}")
        else:
            messagebox.showerror("导入失败", "无法导入扩展包，请检查文件格式")

    def view_pack_content(self):
        """查看扩展包内容"""
        selected = self.pack_list.curselection()
        if not selected:
            messagebox.showwarning("未选择", "请先选择一个扩展包！")
            return
            
        pack_name = self.pack_list.get(selected[0])
        pack_path = ENCOURAGEMENT_PACK_DIR / f"{pack_name}.hl"
        encouragements = load_encouragement_pack(pack_path)
        
        # 创建查看对话框
        view_window = tk.Toplevel(self.root)
        view_window.geometry("630x1570")
        view_window.resizable(False, False)
        view_window.transient(self.root)
        view_window.grab_set()
        
        # 添加全屏按钮
        self.add_fullscreen_button(view_window)
        
        # 主框架
        main_frame = ttk.Frame(view_window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(
            view_window, 
            text=f"{pack_name} 包含以下激励语:", 
            font=("Arial", 10)
        ).pack(pady=15)
        
        frame = ttk.Frame(view_window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(
            frame, 
            yscrollcommand=scrollbar.set
        )
        for msg in encouragements:
            listbox.insert(tk.END, msg)
        listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        
        ttk.Button(
            view_window, 
            text="关闭", 
            command=view_window.destroy,
            style="Secondary.TButton",
            width=15
        ).pack(pady=15)

    def delete_pack(self):
        """删除扩展包"""
        selected = self.pack_list.curselection()
        if not selected:
            messagebox.showwarning("未选择", "请先选择一个扩展包！")
            return
            
        pack_name = self.pack_list.get(selected[0])
        pack_file = ENCOURAGEMENT_PACK_DIR / f"{pack_name}.hl"
        
        if messagebox.askyesno("确认删除", f"确定要删除扩展包 '{pack_name}' 吗？"):
            try:
                pack_file.unlink()
                self.update_pack_list()
                messagebox.showinfo("删除成功", f"扩展包 '{pack_name}' 已删除")
            except Exception as e:
                messagebox.showerror("删除失败", f"无法删除文件: {str(e)}")

    def scan_for_packs(self):
        """扫描扩展包"""
        auto_discover_encouragement_packs()
        self.update_pack_list()
        messagebox.showinfo("扫描完成", "已扫描并导入新的激励语扩展包")

    def apply_history_settings(self):
        """应用历史记录设置"""
        # 获取时间格式设置
        time_format_map = {
            "仅日期": "date",  # 仅日期
            "精确到小时": "hour",  # 精确到小时
            "精确到分钟": "minute",  # 精确到分钟
            "精确到秒": "second"  # 精确到秒
        }
        time_format = time_format_map.get(self.history_time_format_var.get(), "second")
        
        # 获取显示模式设置
        display_mode_map = {
            "显示所有记录": "all",
            "按月显示记录": "monthly"
        }
        display_mode = display_mode_map.get(self.history_display_var.get(), "all")
        
        # 更新全局设置
        self.settings["history_time_format"] = time_format
        self.settings["history_display_mode"] = display_mode
        save_global_settings(self.settings)
        
        # 更新当前历史记录显示
        self.update_history_display()
        messagebox.showinfo("设置成功", "历史记录设置已更新")

    def on_zoom_change(self, value):
        """缩放比例改变时的回调"""
        self.zoom_value_label.config(text=f"{float(value):.1f}x")

    def apply_zoom_and_font(self):
        """应用缩放和字体设置"""
        # 保存设置
        self.settings["zoom_factor"] = self.zoom_factor_var.get()
        self.settings["base_font_size"] = self.font_size_var.get()
        save_global_settings(self.settings)
        
        # 更新应用设置
        self.zoom_factor = self.zoom_factor_var.get()
        self.base_font_size = self.font_size_var.get()
        
        # 应用设置
        self.apply_zoom_factor()
        
        messagebox.showinfo("设置已应用", "缩放比例和字体大小设置已生效！")

    def on_focus_in(self, event):
        """处理焦点进入事件"""
        widget = event.widget
        if isinstance(widget, (tk.Entry, ttk.Entry)):
            self.last_focused_entry = widget
            input_type = "number" if widget in [self.amount_input, self.new_target_input] else "text"
            
            if not self.virtual_keyboard:
                self.virtual_keyboard = VirtualKeyboard(self.root, widget, input_type)
                self.virtual_keyboard.show()
            else:
                self.virtual_keyboard.set_target(widget, input_type)
                if not self.virtual_keyboard.active:
                    self.virtual_keyboard.show()

    def add_fullscreen_button(self, window):
        """添加全屏按钮到窗口"""
        control_frame = ttk.Frame(window)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        fullscreen_btn = ttk.Button(
            control_frame,
            text="全屏" if not self.fullscreen else "退出全屏",
            command=lambda: self.toggle_dialog_fullscreen(window),
            width=8
        )
        fullscreen_btn.pack(side=tk.RIGHT, padx=5)
        
        close_btn = ttk.Button(
            control_frame,
            text="关闭",
            command=window.destroy,
            width=8
        )
        close_btn.pack(side=tk.RIGHT, padx=5)
    
    def toggle_dialog_fullscreen(self, window):
        """切换对话框全屏状态"""
        fullscreen = window.attributes("-fullscreen")
        window.attributes("-fullscreen", not fullscreen)


# 运行应用
if __name__ == "__main__":
    # 确保数据目录存在
    MAIN_DATA_DIR.mkdir(parents=True, exist_ok=True)
    ENCOURAGEMENT_PACK_DIR.mkdir(parents=True, exist_ok=True)
    
    root = tk.Tk()
    app = PiggyBankApp(root)
    root.mainloop()
