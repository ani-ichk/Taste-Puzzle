from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
                             QLabel, QTabWidget, QCheckBox, QComboBox,
                             QMessageBox, QScrollArea, QFrame, QToolBar,
                             QDialog, QLayout, QCompleter)
from PyQt6.QtCore import Qt, QSettings, QSize, QTimer, QRect, QPoint, QStringListModel
from PyQt6.QtGui import QAction, QIcon

from src.database import Recipe
from src.modules.recipe_dialog import RecipeDialog, RecipeCardDialog
from src.modules.settings_dialog import SettingsDialog
from src.modules.help_dialog import HelpDialog
from src.modules.user_profile import ProfileWidget
from src.modules.cart_manager import CartWidget


class SmartSearchLineEdit(QLineEdit):
    """Умное поле поиска с подсказками"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Поиск по названию...")

        # Настраиваем автодополнение
        self.completer = QCompleter([])
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setCompleter(self.completer)

        layout = QHBoxLayout(self)
        layout.addStretch()
        layout.setContentsMargins(5, 0, 5, 0)

        # Добавляем отступ слева для текста
        self.setTextMargins(25, 0, 5, 0)

    def set_search_suggestions(self, suggestions):
        """Устанавливает список подсказок для автодополнения"""
        self.completer.setModel(QStringListModel(suggestions))


# ====================================================================================
# FlowLayout - кастомный layout для расположения виджетов как в веб-потоке
# ====================================================================================
class FlowLayout(QLayout):
    """ Располагает виджеты в потоке слева направо, с переносом на новую строку при нехватке места """

    def __init__(self, parent=None, margin=15, h_spacing=15, v_spacing=15):
        super().__init__(parent)

        # Установка отступов от краев контейнера
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)

        self._h_spacing = h_spacing  # Горизонтальный отступ между виджетами
        self._v_spacing = v_spacing  # Вертикальный отступ между строками
        self._items = []  # Список для хранения элементов layout
        self._geometry_cache = None  # Кэш для геометрии (для оптимизации)

    def __del__(self):
        """Деструктор - очищает все элементы layout при удалении."""
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        """Добавляет элемент в layout и сбрасывает кэш геометрии."""
        self._items.append(item)
        self._geometry_cache = None

    def horizontalSpacing(self):
        """Возвращает значение горизонтального отступа."""
        return self._h_spacing

    def verticalSpacing(self):
        """Возвращает значение вертикального отступа."""
        return self._v_spacing

    def count(self):
        """Возвращает количество элементов в layout."""
        return len(self._items)

    def itemAt(self, index):
        """Возвращает элемент по указанному индексу."""
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        """Удаляет и возвращает элемент по указанному индексу."""
        if 0 <= index < len(self._items):
            item = self._items.pop(index)
            self._geometry_cache = None
            return item
        return None

    def expandingDirections(self):
        """Определяет направления расширения layout (в данном случае не расширяется)."""
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        """Возвращает True, так как высота layout зависит от его ширины."""
        return True

    def heightForWidth(self, width):
        """Вычисляет необходимую высоту layout для заданной ширины."""
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        """Устанавливает геометрию layout и размещает в нем элементы."""
        super().setGeometry(rect)  # Вызов родительского метода
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        """Возвращает рекомендуемый размер layout."""
        return self.minimumSize()

    def minimumSize(self):
        """Вычисляет минимальный размер layout."""
        size = QSize()  # Создаем объект размера
        for item in self._items:
            size = size.expandedTo(item.minimumSize())

        # Добавляем отступы к размеру
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect, test_only):
        """ Основной метод для расстановки элементов в layout.
        rect: Прямоугольная область для размещения
        test_only: Если True, только вычисляет высоту без фактического размещения
        """
        # Получаем реальную рабочую область с учетом отступов
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(+left, +top, -right, -bottom)  # Область внутри отступов
        x = effective_rect.x()  # Текущая позиция X
        y = effective_rect.y()  # Текущая позиция Y
        line_height = 0  # Высота текущей строки

        # Проходим по всем элементам layout
        for item in self._items:
            widget = item.widget()
            if widget is None:
                continue  # Пропускаем элементы без виджета

            space_x = self.horizontalSpacing()  # Горизонтальный отступ
            space_y = self.verticalSpacing()  # Вертикальный отступ

            # Вычисляем позицию для следующего элемента
            next_x = x + item.sizeHint().width() + space_x

            # Если следующий элемент не помещается в текущей строке
            if next_x - space_x > effective_rect.right() and line_height > 0:
                x = effective_rect.x()  # Переходим на новую строку
                y = y + line_height + space_y  # Увеличиваем Y на высоту строки + отступ
                next_x = x + item.sizeHint().width() + space_x  # Пересчитываем next_x
                line_height = 0  # Сбрасываем высоту строки

            # Если не тестовый режим, устанавливаем геометрию элемента
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x  # Обновляем текущую позицию X
            # Обновляем высоту строки (максимальная высота элементов в строке)
            line_height = max(line_height, item.sizeHint().height())

        # Возвращаем общую высоту layout
        return y + line_height - rect.y() + bottom

    def invalidate(self):
        """Сбрасывает кэш геометрии при изменении layout."""
        super().invalidate()
        self._geometry_cache = None


class RecipeCard(QFrame):
    """Виджет карточки рецепта для главного окна"""

    def __init__(self, recipe_data, db, parent=None):
        """ Инициализация карточки рецепта. """
        super().__init__(parent)
        self.recipe_data = recipe_data
        self.db = db
        self.parent = parent
        self.user_id = parent.user_id if parent else None
        self.init_ui()

    def init_ui(self):
        """Инициализация пользовательского интерфейса карточки."""
        self.setFixedWidth(250)
        self.setMinimumHeight(280)
        self.setMaximumHeight(340)

        self.setStyleSheet("""
                    QFrame {
                        background-color: white;
                        border: 1px solid #dee2e6;
                        border-radius: 12px;
                        margin: 0px;
                        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);
                        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
                    }
                    QFrame:hover {
                        box-shadow: 0 8px 25px rgba(52, 152, 219, 0.15);
                        transform: translateY(-3px);
                    }
                    QFrame:pressed {
                        transform: translateY(-1px);
                    }
                """)

        # Создаем вертикальный layout для карточки
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # === ВЕРХНЯЯ ЧАСТЬ: Изображение рецепта ===
        image_container = QWidget()
        image_container.setFixedHeight(150)
        image_container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,  /* Вертикальный градиент */
                    stop:0 #f8f9fa, stop:1 #e9ecef);                /* От светлого к более темному серому */
                border-top-left-radius: 12px;                        /* Закругление верхних углов */
                border-top-right-radius: 12px;                       /* Закругление верхних углов */
                border-bottom: 1px solid #e9ecef;                    /* Нижняя граница */
            }
        """)

        # Создаем layout для изображения
        image_layout = QVBoxLayout(image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pixmap = self.db.get_recipe_image(self.recipe_data[0])
        if pixmap and not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(248, 148, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                          Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.setScaledContents(True)  # Включаем масштабирование содержимого
        else:
            # Текстовую заглушку с названием рецепта
            recipe_name = self.recipe_data[2]
            if len(recipe_name) > 22:
                display_text = recipe_name[:22] + '...'
            else:
                display_text = recipe_name

            self.image_label.setText(f"🍳\n{display_text}")
            self.image_label.setStyleSheet("""
                QLabel {
                    color: #6c757d;          /* Серый цвет текста */
                    font-size: 14px;         /* Размер шрифта */
                    font-weight: 500;        /* Средняя жирность */
                    padding: 20px;           /* Внутренние отступы */
                    line-height: 1.4;        /* Межстрочный интервал */
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,  /* Градиентный фон */
                        stop:0 #e3f2fd, stop:1 #bbdefb);                /* От голубого к светло-голубому */
                }
            """)
            self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        image_layout.addWidget(self.image_label)
        layout.addWidget(image_container)

        # === ЦЕНТРАЛЬНАЯ ЧАСТЬ: Основная информация ===
        info_container = QWidget()
        info_container.setStyleSheet("background-color: white;")
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(15, 15, 15, 15)
        info_layout.setSpacing(10)

        # Название рецепта
        name_label = QLabel(self.recipe_data[2])
        name_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        name_label.setStyleSheet("""
            QLabel {
                font-weight: 600;            /* Полужирный шрифт */
                font-size: 16px;             /* Размер шрифта */
                color: #2c3e50;              /* Темно-синий цвет */
                line-height: 1.3;            /* Межстрочный интервал */
                padding-bottom: 5px;         /* Нижний отступ */
                border-bottom: 1px solid #f1f3f4;  /* Нижняя граница */
            }
        """)
        name_label.setWordWrap(True)
        name_label.setMinimumHeight(45)
        name_label.setMaximumHeight(60)
        info_layout.addWidget(name_label)

        # === БЛОК МЕТА-ИНФОРМАЦИИ ===
        meta_container = QWidget()
        meta_container.setStyleSheet("background-color: white;")
        meta_layout = QVBoxLayout(meta_container)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(8)

        # кухня и время
        info_row = QHBoxLayout()
        info_row.setContentsMargins(0, 0, 0, 0)
        info_row.setSpacing(10)

        # Кухня
        cuisine = self.recipe_data[17] if len(self.recipe_data) > 17 else None
        if cuisine:
            cuisine_widget = QWidget()
            cuisine_widget.setFixedHeight(24)
            cuisine_widget.setStyleSheet("""
                        QWidget {
                            background-color: #e8f5e9;
                            border-radius: 4px;
                            border: 1px solid #c8e6c9;
                        }
                    """)

            cuisine_layout = QHBoxLayout(cuisine_widget)
            cuisine_layout.setContentsMargins(6, 2, 6, 2)
            cuisine_label = QLabel(f"🌍 {cuisine[:12]}" if len(cuisine) > 12 else f"🌍 {cuisine}")
            cuisine_label.setStyleSheet("font-size: 10px; font-weight: 500; color: #2e7d32;")
            cuisine_label.setToolTip(f"Кухня: {cuisine}")
            cuisine_layout.addWidget(cuisine_label)
            info_row.addWidget(cuisine_widget)

        # Время приготовления
        time_widget = QWidget()
        time_widget.setFixedHeight(24)
        time_widget.setStyleSheet("""
                    QWidget {
                        background-color: #e3f2fd;
                        border-radius: 4px;
                        border: 1px solid #bbdefb;
                    }
                """)

        time_layout = QHBoxLayout(time_widget)
        time_layout.setContentsMargins(6, 2, 6, 2)
        time_label = QLabel(f"⏱{self.recipe_data[8] or '?'}м")
        time_label.setStyleSheet("font-size: 10px; font-weight: 500; color: #1976d2;")
        time_layout.addWidget(time_label)
        info_row.addWidget(time_widget)

        info_row.addStretch()
        meta_layout.addLayout(info_row)

        # === БЛОК СТАТУСОВ ===
        status_container = QWidget()
        status_container.setFixedHeight(90)
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(10)

        # Кнопка "Избранное"
        self.is_favorite = self.recipe_data[15] if len(self.recipe_data) > 15 else False
        self.favorite_btn = QPushButton("❤️" if self.is_favorite else "🤍")
        self.favorite_btn.setFixedSize(50, 50)
        # Стили для кнопки избранного
        self.favorite_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;      /* Прозрачный фон */
                border: none;                       
                border-radius: 2px;                /* Круглая кнопка */
                font-size: 17px;                    /* Размер шрифта */
            }
            QPushButton:hover {
                background-color: rgba(220, 53, 69, 0.1); 
                transform: scale(1.1);                    
            }
        """)
        self.favorite_btn.setToolTip("В избранном" if self.is_favorite else "Добавить в избранное")
        self.favorite_btn.clicked.connect(self.toggle_favorite_status)

        self.is_cooked = self.recipe_data[16] if len(self.recipe_data) > 16 else False
        self.cooked_btn = QPushButton("✅" if self.is_cooked else "⏳")
        self.cooked_btn.setFixedSize(50, 50)
        self.cooked_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;      /* Прозрачный фон */
                border: none;                       /* Без рамки */
                border-radius: 2px;                /* Круглая кнопка */
                font-size: 18px;                    /* Размер шрифта */
            }
            QPushButton:hover {
                background-color: rgba(40, 167, 69, 0.1);  /* Зеленый фон при наведении */
                transform: scale(1.1);                     /* Увеличение при наведении */
            }
        """)
        self.cooked_btn.setToolTip("Приготовлено" if self.is_cooked else "Отметить как приготовленное")
        self.cooked_btn.clicked.connect(self.toggle_cooked_status)

        dish_type = self.recipe_data[18] if len(self.recipe_data) > 18 else "Без категории"
        dish_type_widget = QWidget()
        dish_type_widget.setFixedHeight(24)
        dish_type_widget.setStyleSheet("""
                    QWidget {
                        background-color: #f3e5f5;
                        border-radius: 4px;
                        border: 1px solid #e1bee7;
                    }
                """)

        dish_type_layout = QHBoxLayout(dish_type_widget)
        dish_type_layout.setContentsMargins(6, 2, 6, 2)

        type_icons = {
            "Салаты": "🥗",
            "Десерты": "🍰",
            "Основные блюда": "🍛",
            "Завтраки": "🍳",
            "Гарниры": "🥔",
            "Супы": "🍲"
        }
        icon = type_icons.get(dish_type, "🍽️")

        dish_type_label = QLabel(f"{icon} {dish_type[:12]}" if len(dish_type) > 12 else f"{icon} {dish_type}")
        dish_type_label.setStyleSheet("font-size: 10px; font-weight: 500; color: #7b1fa2;")
        dish_type_label.setToolTip(f"Тип блюда: {dish_type}")
        dish_type_layout.addWidget(dish_type_label)

        status_layout.addWidget(self.favorite_btn)
        status_layout.addWidget(self.cooked_btn)
        status_layout.addWidget(dish_type_widget)
        status_layout.addStretch()

        meta_layout.addWidget(status_container)
        info_layout.addWidget(meta_container)

        layout.addWidget(info_container)

        # === ОСНОВАНИЕ КАРТОЧКИ ===
        bottom_line = QWidget()
        bottom_line.setFixedHeight(4)
        bottom_line.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,  /* Горизонтальный градиент */
                    stop:0 #3498db, stop:1 #2ecc71);                /* От синего к зеленому */
                border-bottom-left-radius: 12px;                     /* Закругление нижних углов */
                border-bottom-right-radius: 12px;                    /* Закругление нижних углов */
            }
        """)
        layout.addWidget(bottom_line)

        self.setLayout(layout)

    def toggle_favorite_status(self):
        """Переключает статус избранного для рецепта."""
        try:
            if self.user_id:
                new_status = not self.is_favorite
                success = self.db.toggle_favorite(self.user_id, self.recipe_data[0])

                if success:
                    self.is_favorite = new_status
                    self.favorite_btn.setText("❤️" if new_status else "🤍")
                    self.favorite_btn.setToolTip("В избранном" if new_status else "Добавить в избранное")

                    # Обновляем данные в recipe_data для синхронизации
                    if len(self.recipe_data) > 15:
                        self.recipe_data = list(self.recipe_data)
                        self.recipe_data[15] = new_status
                        self.recipe_data = tuple(self.recipe_data)

                    # Обновляем статистику в профиле
                    if self.parent and hasattr(self.parent, 'profile_widget'):
                        self.parent.profile_widget.update_profile()

        except Exception as e:
            print(f"Ошибка при переключении статуса избранного: {e}")

    def toggle_cooked_status(self):
        """Переключает статус приготовленного для рецепта."""
        try:
            if self.user_id:
                new_status = not self.is_cooked
                success = self.db.mark_recipe_as_cooked(self.user_id, self.recipe_data[0], new_status)

                if success:
                    self.is_cooked = new_status
                    self.cooked_btn.setText("✅" if new_status else "⏳")
                    self.cooked_btn.setToolTip("Приготовлено" if new_status else "Отметить как приготовленное")

                    if len(self.recipe_data) > 16:
                        self.recipe_data = list(self.recipe_data)
                        self.recipe_data[16] = new_status
                        self.recipe_data = tuple(self.recipe_data)

                    # Обновляем статистику в профиле
                    if self.parent and hasattr(self.parent, 'profile_widget'):
                        self.parent.profile_widget.update_profile()

        except Exception as e:
            print(f"Ошибка при переключении статуса приготовления: {e}")

    def mouseDoubleClickEvent(self, event):
        self.parent.view_recipe(self.recipe_data)


class AutoCompleteComboBox(QComboBox):
    """ComboBox с автодополнением и возможностью ввода нескольких значений"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.completer = self.completer()
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)

        # Разрешаем ввод нескольких значений через запятую
        self.lineEdit().textChanged.connect(self.on_text_changed)

    def on_text_changed(self, text):
        """Обрабатывает изменение текста для автодополнения"""
        if ',' in text:
            # Если введена запятая, оставляем только последнюю часть для автодополнения
            last_part = text.split(',')[-1].strip()
            if last_part:
                self.completer.setCompletionPrefix(last_part)
                if self.completer.completionCount() > 0:
                    self.completer.complete()

    def text(self):
        """Возвращает текущий текст комбобокса"""
        return self.currentText()


class MainWindow(QMainWindow):
    """Главное окно приложения с вкладками рецептов, профиля и корзины."""

    def __init__(self, db, user_id, logout_callback):
        super().__init__()
        self.db = db
        self.user_id = user_id
        self.logout_callback = logout_callback

        self.settings = QSettings("PuzzleVkusov", "AppSettings")
        self.current_recipe_cards = []

        self.filter_timer = QTimer()
        self.filter_timer.setSingleShot(True)
        self.filter_timer.timeout.connect(self.load_recipes)

        self.init_ui()
        self.load_initial_settings()
        self.load_recipes()
        self.update_profile()

    def init_ui(self):
        self.setWindowTitle("Пазл Вкусов")
        self.setMinimumSize(1200, 850)
        self.setWindowIcon(QIcon("../img/icon.ico"))

        font_size = self.settings.value("font_size", 14, type=int)
        title_font_size = self.settings.value("title_font_size", 16, type=int)

        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: #f8f9fa;
            }}
            QWidget {{
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: {font_size}px;
            }}
            /* Стили для полей поиска */
            QLineEdit {{
                padding: 8px;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
            }}
            QLineEdit:focus {{
                border: 1px solid #007bff;
                outline: none;
            }}
            QComboBox {{
                padding: 8px;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
            }}
            QComboBox:focus {{
                border: 1px solid #007bff;
                outline: none;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
                selection-background-color: #007bff;
                selection-color: white;
            }}
            QWidget {{
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: {font_size}px;
            }}
            QTabWidget::pane {{
                border: 1px solid #dee2e6;
                background-color: white;
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background-color: #e9ecef;
                color: #495057;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: {font_size}px;
            }}
            QTabBar::tab:selected {{
                background-color: white;
                color: #495057;
                border-bottom: 2px solid #007bff;
            }}
            QPushButton {{
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 500;
                font-size: {font_size}px;
            }}
            QPushButton:hover {{
                background-color: #0056b3;
            }}
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}
        """)

        self.setMenuBar(None)
        self.create_toolbar()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)

        self.tabs = QTabWidget()

        # === ВКЛАДКА РЕЦЕПТОВ ===
        recipes_tab = QWidget()
        recipes_layout = QVBoxLayout(recipes_tab)
        recipes_layout.setContentsMargins(0, 0, 0, 0)
        recipes_layout.setSpacing(10)

        self.setup_recipe_filters(recipes_layout)

        # Панель управления рецептами
        recipes_control_layout = QHBoxLayout()
        add_recipe_btn = QPushButton("➕ Добавить рецепт")
        add_recipe_btn.clicked.connect(self.add_recipe)
        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.clicked.connect(self.load_recipes)

        recipes_control_layout.addWidget(add_recipe_btn)
        recipes_control_layout.addWidget(refresh_btn)
        recipes_control_layout.addStretch()
        recipes_layout.addLayout(recipes_control_layout)

        # Область прокрутки для рецептов
        self.recipes_scroll = QScrollArea()
        self.recipes_scroll.setWidgetResizable(True)
        self.recipes_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.recipes_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Главный контейнер для всех рецептов
        self.recipes_container = QWidget()
        self.recipes_container_layout = QVBoxLayout(self.recipes_container)
        self.recipes_container_layout.setSpacing(20)
        self.recipes_container_layout.setContentsMargins(10, 10, 10, 10)
        self.recipes_container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.recipes_scroll.setWidget(self.recipes_container)

        # Устанавливаем стили для скролла
        self.recipes_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #f1f3f4;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #c1c1c1;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a8a8a8;
            }
        """)

        recipes_layout.addWidget(self.recipes_scroll, 1)

        # === ВКЛАДКА ПРОФИЛЯ ===
        self.profile_widget = ProfileWidget(self.db, self.user_id, self)

        # === ВКЛАДКА КОРЗИНЫ ===
        self.cart_widget = CartWidget(self.db, self.user_id, self)

        self.tabs.addTab(recipes_tab, "📖 Рецепты")
        self.tabs.addTab(self.profile_widget, "👤 Профиль")
        self.tabs.addTab(self.cart_widget, "🛒 Корзина")

        layout.addWidget(self.tabs, 1)
        central_widget.setLayout(layout)

    def load_initial_settings(self):
        # Загружает начальные настройки приложения при запуске
        try:
            font_size = self.settings.value("font_size", 14, type=int)
            title_font_size = self.settings.value("title_font_size", 16, type=int)
            self.update_styles(font_size, title_font_size)
        except Exception as e:
            print(f"Ошибка загрузки начальных настроек: {e}")

    def create_toolbar(self):
        # Создает панель инструментов с иконками в верхней части окна
        toolbar = QToolBar("Главное меню")
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #f8f9fa;          /* Светло-серый фон */
                border-bottom: 1px solid #dee2e6;   /* Нижняя граница */
                spacing: 5px;                       /* Отступы между элементами */
                padding: 5px;                       /* Внутренние отступы */
            }
            QToolButton {
                padding: 5px;                       /* Внутренние отступы кнопок */
                border-radius: 4px;                 /* Закругленные углы */
                background-color: transparent;      /* Прозрачный фон */
            }
            QToolButton:hover {
                background-color: #e9ecef;          /* Светло-серый фон при наведении */
            }
        """)

        def create_action(icon_name, fallback_text, tooltip, callback):
            """Создает действие с иконкой или текстовой заменой."""
            icon_path = f"../img/{icon_name}"
            if icon_path:
                action = QAction(QIcon(icon_path), "", self)
            else:
                action = QAction(fallback_text, self)

            action.triggered.connect(callback)
            action.setToolTip(tooltip)
            action.setStatusTip(tooltip)
            return action

        settings_action = create_action("settings_icon.png", "⚙️", "Настройки приложения", self.open_settings)
        help_action = create_action("help_icon.png", "❓", "Справка", self.open_help)
        refresh_action = create_action("refresh_icon.png", "🔄", "Обновить данные", self.refresh_data)

        toolbar.addAction(settings_action)
        toolbar.addAction(help_action)
        toolbar.addAction(refresh_action)

        self.addToolBar(toolbar)
        toolbar.setIconSize(QSize(24, 24))

    def setup_recipe_filters(self, layout):
        # Настраивает панель фильтрации рецептов с чекбоксами для ингредиентов
        filters_container = QWidget()
        filters_container.setFixedHeight(150)
        filters_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #dee2e6;
            }
        """)

        filters_layout = QVBoxLayout(filters_container)
        filters_layout.setContentsMargins(15, 10, 15, 10)

        # Первая строка фильтров
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(10)

        row1_layout.addWidget(QLabel("Кухня:"))
        self.cuisine_filter = QComboBox()
        self.cuisine_filter.setMinimumWidth(150)
        self.cuisine_filter.addItem("Любая кухня")
        self.load_cuisines_to_filter()
        self.cuisine_filter.currentTextChanged.connect(lambda: self.apply_filters(immediate=True))
        row1_layout.addWidget(self.cuisine_filter)

        row1_layout.addWidget(QLabel("Время:"))
        self.time_filter = QComboBox()
        self.time_filter.setMinimumWidth(120)
        self.time_filter.addItems(["Любое", "15 мин", "30 мин", "60 мин", "90 мин", "120 мин"])
        self.time_filter.currentTextChanged.connect(lambda: self.apply_filters(immediate=True))
        row1_layout.addWidget(self.time_filter)

        self.favorites_only = QCheckBox("Только избранное")
        self.favorites_only.stateChanged.connect(lambda: self.apply_filters(immediate=True))
        row1_layout.addWidget(self.favorites_only)

        self.cooked_only = QCheckBox("Только приготовленные")
        self.cooked_only.stateChanged.connect(lambda: self.apply_filters(immediate=True))
        row1_layout.addWidget(self.cooked_only)

        row1_layout.addStretch()
        filters_layout.addLayout(row1_layout)

        # Вторая строка поиск
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(10)

        row2_layout.addWidget(QLabel("Название:"))
        self.name_filter = SmartSearchLineEdit()
        self.name_filter.setMinimumWidth(250)
        self.name_filter.textChanged.connect(lambda: self.apply_filters(debounced=True))
        self.load_search_suggestions()

        clear_name_btn = QPushButton("🗑️")
        clear_name_btn.setFixedSize(50, 40)
        clear_name_btn.setToolTip("Очистить поле названия")
        clear_name_btn.clicked.connect(self.clear_name_filter)

        row2_layout.addWidget(self.name_filter)
        row2_layout.addWidget(clear_name_btn)
        row2_layout.addStretch()

        filters_layout.addLayout(row2_layout)

        # Третья строка - фильтр по ингредиентам
        row3_layout = QHBoxLayout()
        row3_layout.setSpacing(10)

        row3_layout.addWidget(QLabel("Ингредиенты:"))

        self.ingredients_filter_container = QWidget()
        self.ingredients_filter_container.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border-radius: 6px;
                border: 1px solid #dee2e6;
                padding: 5px;
            }
        """)

        self.ingredients_checkbox_layout = QHBoxLayout(self.ingredients_filter_container)
        self.ingredients_checkbox_layout.setSpacing(10)
        self.ingredients_checkbox_layout.setContentsMargins(5, 5, 5, 5)

        self.ingredient_filter_btn = QPushButton("📋 Выбрать ингредиенты")
        self.ingredient_filter_btn.clicked.connect(self.show_ingredients_selection)
        self.ingredient_filter_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)

        clear_ingredients_btn = QPushButton("🗑️")
        clear_ingredients_btn.setFixedSize(50, 40)
        clear_ingredients_btn.setToolTip("Очистить выбор ингредиентов")
        clear_ingredients_btn.clicked.connect(self.clear_ingredients_filter)

        row3_layout.addWidget(self.ingredient_filter_btn)
        row3_layout.addWidget(self.ingredients_filter_container, 1)
        row3_layout.addWidget(clear_ingredients_btn)

        filters_layout.addLayout(row3_layout)

        layout.addWidget(filters_container)

    def show_ingredients_selection(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Выбор ингредиентов для фильтрации")
        dialog.setModal(True)
        dialog.resize(500, 600)

        layout = QVBoxLayout(dialog)

        search_layout = QHBoxLayout()
        search_input = QLineEdit()
        search_input.setPlaceholderText("Поиск ингредиентов...")
        search_layout.addWidget(search_input)

        # Область с чекбоксами
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        self.ingredients_list_layout = QVBoxLayout(scroll_widget)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)

        # Загружаем ингредиенты
        self.load_ingredients_for_checkboxes()

        button_layout = QHBoxLayout()
        select_all_btn = QPushButton("Выбрать все")
        select_all_btn.clicked.connect(self.select_all_ingredients)
        clear_all_btn = QPushButton("Снять все")
        clear_all_btn.clicked.connect(self.clear_all_ingredients)
        apply_btn = QPushButton("Применить")
        apply_btn.clicked.connect(lambda: self.apply_ingredients_filter(dialog))
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(clear_all_btn)
        button_layout.addStretch()
        button_layout.addWidget(apply_btn)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(search_layout)
        layout.addWidget(scroll_area)
        layout.addLayout(button_layout)

        dialog.exec()

    def load_ingredients_for_checkboxes(self):
        """Загружает ингредиенты для чекбоксов"""
        try:
            # Очищаем layout
            while self.ingredients_list_layout.count():
                item = self.ingredients_list_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Получаем ингредиенты
            ingredients = self.db.get_ingredients()

            # Сортируем по алфавиту
            ingredients.sort(key=lambda x: x[1].lower())

            # Создаем чекбоксы
            self.ingredient_checkboxes = {}
            for ing_id, ing_name in ingredients:
                checkbox = QCheckBox(ing_name)
                checkbox.setObjectName(f"ing_{ing_id}")
                self.ingredients_list_layout.addWidget(checkbox)
                self.ingredient_checkboxes[ing_name] = checkbox

            # Добавляем растягивающийся элемент
            self.ingredients_list_layout.addStretch()

        except Exception as e:
            print(f"Ошибка загрузки ингредиентов для чекбоксов: {e}")

    def select_all_ingredients(self):
        """Выбирает все ингредиенты"""
        for checkbox in self.ingredient_checkboxes.values():
            checkbox.setChecked(True)

    def clear_all_ingredients(self):
        """Снимает выбор со всех ингредиентов"""
        for checkbox in self.ingredient_checkboxes.values():
            checkbox.setChecked(False)

    def apply_ingredients_filter(self, dialog):
        """Применяет выбранные ингредиенты"""
        selected_ingredients = []

        # Собираем выбранные ингредиенты
        for ing_name, checkbox in self.ingredient_checkboxes.items():
            if checkbox.isChecked():
                selected_ingredients.append(ing_name)

        self.update_selected_ingredients_display(selected_ingredients)

        dialog.accept()
        self.load_recipes()

    def update_selected_ingredients_display(self, selected_ingredients):
        """Обновляет отображение выбранных ингредиентов"""
        # Очищаем контейнер
        while self.ingredients_checkbox_layout.count():
            item = self.ingredients_checkbox_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Добавляем выбранные ингредиенты в виде маленьких виджетов
        for i, ingredient in enumerate(selected_ingredients[:5]):  # Показываем до 5
            label = QLabel(f"• {ingredient}")
            label.setStyleSheet("""
                QLabel {
                    background-color: #e9ecef;
                    border-radius: 12px;
                    padding: 3px 8px;
                    font-size: 11px;
                    color: #495057;
                    margin-right: 5px;
                }
            """)
            self.ingredients_checkbox_layout.addWidget(label)

        # Если больше 5, показываем многоточие
        if len(selected_ingredients) > 5:
            label = QLabel(f"... ещё {len(selected_ingredients) - 5}")
            label.setStyleSheet("""
                QLabel {
                    background-color: #e9ecef;
                    border-radius: 12px;
                    padding: 3px 8px;
                    font-size: 11px;
                    color: #6c757d;
                    margin-right: 5px;
                }
            """)
            self.ingredients_checkbox_layout.addWidget(label)

        # Сохраняем выбранные ингредиенты
        self.selected_ingredients = selected_ingredients

        # Обновляем текст кнопки
        if selected_ingredients:
            self.ingredient_filter_btn.setText(f"📋 Выбрано: {len(selected_ingredients)}")
        else:
            self.ingredient_filter_btn.setText("📋 Выбрать ингредиенты")

    def load_search_suggestions(self):
        """Загружает подсказки для поиска по названиям рецептов"""
        try:
            # Получаем все рецепты для подсказок
            session = self.db.Session()
            recipes = session.query(Recipe).all()
            recipe_names = [recipe.name for recipe in recipes]
            session.close()

            # Устанавливаем подсказки
            self.name_filter.set_search_suggestions(recipe_names)

        except Exception as e:
            print(f"Ошибка загрузки подсказок для поиска: {e}")

    def load_cuisines_to_filter(self):
        """Загружает список кухонь в фильтр"""
        try:
            cuisines = self.db.get_cuisines()

            self.cuisine_filter.clear()
            self.cuisine_filter.addItem("Любая кухня")

            if cuisines:
                for cuisine_id, cuisine_name in cuisines:
                    self.cuisine_filter.addItem(cuisine_name)
            else:
                default_cuisines = ["Русская", "Итальянская", "Японская",
                                    "Китайская", "Мексиканская", "Французская"]
                for cuisine in default_cuisines:
                    self.cuisine_filter.addItem(cuisine)

        except Exception as e:
            print(f"Ошибка загрузки кухонь: {e}")

    def clear_ingredients_filter(self):
        """Очищает выбор ингредиентов"""
        self.selected_ingredients = []
        self.update_selected_ingredients_display([])
        self.load_recipes()

    def clear_name_filter(self):
        """Очищает поле фильтра по названию"""
        self.name_filter.clear()
        self.load_recipes()

    def apply_filters(self, immediate=False, debounced=False):
        """Применяет фильтры"""
        if debounced:
            if hasattr(self, 'filter_timer'):
                self.filter_timer.stop()
                self.filter_timer.start(500)
        else:
            self.load_recipes()

    def reset_filters(self):
        """Сбрасывает все фильтры"""
        self.cuisine_filter.setCurrentIndex(0)
        self.time_filter.setCurrentIndex(0)
        self.favorites_only.setChecked(False)
        self.cooked_only.setChecked(False)
        self.ingredient_filter.lineEdit().clear()
        self.name_filter.clear()
        self.load_recipes()

    def load_recipes(self):
        """Загружает рецепты с учетом фильтров и группирует по типам блюд"""
        try:
            # Получаем значения фильтров
            cuisine = self.cuisine_filter.currentText()
            if cuisine == "Любая кухня":
                cuisine = None

            time_filter = self.time_filter.currentText()
            max_time = None
            if time_filter != "Любое":
                time_map = {
                    "15 мин": 15,
                    "30 мин": 30,
                    "60 мин": 60,
                    "90 мин": 90,
                    "120 мин": 120
                }
                max_time = time_map.get(time_filter)

            favorites_only = self.favorites_only.isChecked()
            cooked_only = self.cooked_only.isChecked()

            # Используем выбранные ингредиенты
            ingredient_filter = self.selected_ingredients if hasattr(self, 'selected_ingredients') else []

            name_filter = self.name_filter.text().strip()

            # Получаем сгруппированные рецепты
            grouped_recipes = self.db.get_recipes_with_filters(
                self.user_id,
                cuisine=cuisine,
                max_time=max_time,
                favorites_only=favorites_only,
                cooked_only=cooked_only,
                ingredient_filter=ingredient_filter,
                name_filter=name_filter
            )

            # Проверяем, что grouped_recipes не является None
            if grouped_recipes is None:
                grouped_recipes = {}

            self.display_recipes_by_category(grouped_recipes)

            self.load_search_suggestions()

        except Exception as e:
            self.show_error_message(f"Ошибка загрузки рецептов: {str(e)}")

    def display_recipes_by_category(self, grouped_recipes):
        """Отображает рецепты, сгруппированные по категориям"""
        self.clear_recipe_container()

        if not grouped_recipes:
            self.show_no_recipes_message()
            return

        priority_categories = [
            "Салаты",
            "Десерты",
            "Основные блюда",
            "Завтраки",
            "Гарниры",
            "Супы",
            "Закуски",
            "Напитки",
            "Соусы"
        ]

        total_recipes = 0

        # Сначала показываем приоритетные категории в заданном порядке
        for category in priority_categories:
            if category in grouped_recipes and grouped_recipes[category]:
                recipes = grouped_recipes[category]
                total_recipes += len(recipes)
                self.create_category_section(category, recipes)
                # Удаляем категорию из grouped_recipes, чтобы не показывать её дважды
                del grouped_recipes[category]

        # Затем показываем оставшиеся категории в алфавитном порядке
        other_categories = sorted(grouped_recipes.keys())
        for category in other_categories:
            if grouped_recipes[category]:
                recipes = grouped_recipes[category]
                total_recipes += len(recipes)
                self.create_category_section(category, recipes)

        self.recipes_container_layout.addStretch()

    def create_category_section(self, category, recipes):
        """Создает секцию для категории с рецептами"""
        category_section = QWidget()
        category_section.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)

        category_layout = QVBoxLayout(category_section)
        category_layout.setContentsMargins(0, 0, 0, 0)
        category_layout.setSpacing(10)

        # Заголовок категории
        header = QLabel(f"{self.get_category_icon(category)} {category} ({len(recipes)})")
        header.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px 15px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(52, 152, 219, 0.1), 
                    stop:1 rgba(46, 204, 113, 0.1));
                border-radius: 8px;
                border-left: 4px solid #3498db;
            }
        """)
        category_layout.addWidget(header)

        # Контейнер для карточек этой категории
        cards_container = QWidget()
        cards_container.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)

        # Используем FlowLayout для карточек
        flow_layout = FlowLayout(cards_container, margin=15, h_spacing=15, v_spacing=15)
        cards_container.setLayout(flow_layout)

        # Добавляем карточки
        for recipe in recipes:
            card = RecipeCard(recipe, self.db, self)
            flow_layout.addWidget(card)
            self.current_recipe_cards.append(card)

        category_layout.addWidget(cards_container)

        # Добавляем разделитель между категориями
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("""
            QFrame {
                background-color: #dee2e6;
                max-height: 1px;
                margin: 20px 0;
            }
        """)
        category_layout.addWidget(separator)

        # Добавляем всю секцию в основной контейнер
        self.recipes_container_layout.addWidget(category_section)

    def get_category_icon(self, category):
        icons = {
            "Салаты": "🥗",
            "Десерты": "🍰",
            "Основные блюда": "🍛",
            "Завтраки": "🍳",
            "Гарниры": "🥔",
            "Супы": "🍲",
            "Закуски": "🥪",
            "Напитки": "🥤",
            "Соусы": "🥫"
        }
        return icons.get(category, "🍽️")

    def clear_recipe_container(self):
        """Очищает контейнер рецептов"""
        while self.recipes_container_layout.count():
            item = self.recipes_container_layout.takeAt(0)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'deleteLater'):
                    widget.deleteLater()
                else:
                    widget.setParent(None)

        self.current_recipe_cards = []

    def show_no_recipes_message(self):
        """Показывает сообщение об отсутствии рецептов"""
        self.clear_recipe_container()

        message_container = QWidget()
        message_container.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)

        message_layout = QVBoxLayout(message_container)
        message_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_layout.setContentsMargins(50, 100, 50, 100)

        icon = QLabel("🔍")
        icon.setStyleSheet("font-size: 64px; color: #6c757d; opacity: 0.5;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Рецептов не найдено")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                color: #495057;
                font-weight: 600;
                margin-top: 20px;
                margin-bottom: 10px;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        description = QLabel("Измените параметры фильтрации или добавьте новый рецепт")
        description.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #6c757d;
                line-height: 1.5;
            }
        """)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)

        add_button = QPushButton("➕ Добавить рецепт")
        add_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 16px;
                margin-top: 30px;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #2980b9;
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(52, 152, 219, 0.2);
            }
        """)
        add_button.clicked.connect(self.add_recipe)

        message_layout.addWidget(icon)
        message_layout.addWidget(title)
        message_layout.addWidget(description)
        message_layout.addWidget(add_button, 0, Qt.AlignmentFlag.AlignCenter)

        self.recipes_container_layout.addWidget(message_container)
        self.recipes_container_layout.addStretch()

    def show_error_message(self, error_text):
        """Показывает сообщение об ошибке"""
        self.clear_recipe_container()

        error_container = QWidget()
        error_container.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)

        error_layout = QVBoxLayout(error_container)
        error_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_layout.setContentsMargins(50, 100, 50, 100)

        icon = QLabel("⚠️")
        icon.setStyleSheet("font-size: 64px; color: #dc3545; opacity: 0.7;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Ошибка загрузки")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                color: #dc3545;
                font-weight: 600;
                margin-top: 20px;
                margin-bottom: 10px;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        description = QLabel(f"Не удалось загрузить рецепты:\n{error_text}")
        description.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #6c757d;
                line-height: 1.5;
                padding: 20px;
                background-color: #f8d7da;
                border-radius: 8px;
                border: 1px solid #f5c6cb;
                margin-bottom: 20px;
            }
        """)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)

        retry_button = QPushButton("🔄 Попробовать снова")
        retry_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 16px;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #0056b3;
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0, 123, 255, 0.2);
            }
        """)
        retry_button.clicked.connect(self.load_recipes)

        error_layout.addWidget(icon)
        error_layout.addWidget(title)
        error_layout.addWidget(description)
        error_layout.addWidget(retry_button, 0, Qt.AlignmentFlag.AlignCenter)

        self.recipes_container_layout.addWidget(error_container)
        self.recipes_container_layout.addStretch()

    def load_cuisines(self):
        """Загружает список кухонь из базы данных"""
        try:
            cuisines = self.db.get_cuisines()
            self.cuisine_filter.clear()
            self.cuisine_filter.addItem("Любая кухня")

            for cuisine_id, cuisine_name in cuisines:
                self.cuisine_filter.addItem(cuisine_name)

        except Exception:
            self.cuisine_filter.addItems(["Любая кухня", "Русская", "Итальянская", "Японская",
                                          "Китайская", "Мексиканская", "Французская", "Американская"])

    def logout(self):
        """ Обрабатывает выход пользователя """
        reply = QMessageBox.question(
            self,
            "Подтверждение выхода",
            "Вы действительно хотите выйти из аккаунта?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.logout_callback()

    def clear_recipe_cards(self):
        """Очищает все карточки рецептов из layout и удаляет их."""
        for card in self.current_recipe_cards:
            self.flow_layout.removeWidget(card)
            card.deleteLater()
        self.current_recipe_cards.clear()

    def center_cards(self):
        """Центрирует карточки, если их мало (менее 4)."""
        if len(self.current_recipe_cards) < 4:
            container = QWidget()
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)

            # Добавляем растягивающееся пространство слева
            container_layout.addStretch()

            # Добавляем все карточки
            for card in self.current_recipe_cards:
                container_layout.addWidget(card)

            # Добавляем растягивающееся пространство справа
            container_layout.addStretch()

            self.clear_recipe_cards()
            self.flow_layout.addWidget(container)

    def update_profile(self):
        """Обновляет данные профиля пользователя."""
        if hasattr(self, 'profile_widget'):
            self.profile_widget.update_profile()

    def open_settings(self):
        """Открывает диалог настроек приложения."""
        try:
            dialog = SettingsDialog(self.db, self.user_id, self)
            dialog.settings_updated.connect(self.apply_settings)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть настройки: {str(e)}")

    def apply_settings(self, settings_data):
        """Применяет настройки из диалога настроек."""
        try:
            font_size = settings_data.get('font_size', 10)
            title_font_size = settings_data.get('title_font_size', 14)

            self.update_styles(font_size, title_font_size)

            self.load_recipes()

            QMessageBox.information(self, "Успех", "Настройки применены!")

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", "Не удалось применить некоторые настройки")

    def update_styles(self, font_size=10, title_font_size=14):
        """Обновляет стили приложения с новыми размерами шрифтов."""
        try:
            base_style = f"""
                QMainWindow {{
                    background-color: #f8f9fa;          
                }}
                QWidget {{
                    font-family: 'Segoe UI', Arial, sans-serif;  
                    font-size: {font_size}px;                    
                }}
                QTabWidget::pane {{
                    border: 1px solid #dee2e6;          
                    background-color: white;            
                    border-radius: 8px;                 
                }}
                QTabBar::tab {{
                    background-color: #e9ecef;          
                    color: #495057;                     
                    padding: 8px 16px;                  
                    margin-right: 2px;                  
                    border-top-left-radius: 4px;        
                    border-top-right-radius: 4px;       
                    font-size: {font_size}px;           
                }}
                QTabBar::tab:selected {{
                    background-color: white;            
                    color: #495057;                     
                    border-bottom: 2px solid #007bff;   
                }}
                QPushButton {{
                    background-color: #007bff;          
                    color: white;                       
                    border: none;                       
                    padding: 8px 16px;                  
                    border-radius: 4px;                 
                    font-weight: 500;                  
                    font-size: {font_size}px;           
                }}
                QPushButton:hover {{
                    background-color: #0056b3;          
                }}
                QLabel {{
                    font-size: {font_size}px;          
                }}
                QLineEdit, QTextEdit, QSpinBox, QComboBox {{
                    font-size: {font_size}px;           
                    padding: 6px;                       
                }}
                .header {{
                    font-size: {title_font_size}px;     
                    font-weight: bold;                  
                }}
            """
            self.setStyleSheet(base_style)

        except Exception as e:
            print(f"Ошибка обновления стилей: {e}")

    def open_help(self):
        """Открывает диалог справки приложения."""
        try:
            # Создаем диалог справки
            dialog = HelpDialog(self)
            dialog.exec()  # Показываем диалог
        except Exception as e:
            print(f"Ошибка открытия справки: {e}")
            QMessageBox.critical(self, "Ошибка", "Не удалось открыть справку")

    def on_settings_updated(self):
        """Обработчик обновления настроек (запрос перезагрузки приложения)."""
        QMessageBox.information(self, "Перезагрузка", "Пожалуйста, перезапустите приложение для применения настроек.")

    def refresh_data(self):
        """Обновляет все данные приложения (рецепты, профиль, корзину)."""
        self.load_recipes()
        self.update_profile()
        if hasattr(self, 'cart_widget'):
            self.cart_widget.update_cart()

    def add_recipe(self):
        """Открывает диалог добавления нового рецепта и обновляет автодополнение"""
        try:
            dialog = RecipeDialog(self.db, self.user_id)
            dialog.recipe_saved.connect(self.load_recipes)
            dialog.recipe_saved.connect(self.update_profile)
            dialog.exec()
        except Exception as e:
            print(f"Ошибка при добавлении рецепта: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при добавлении рецепта: {e}")

    def view_recipe(self, recipe_data):
        """Открывает диалог просмотра рецепта в виде карточки."""
        try:
            dialog = RecipeCardDialog(recipe_data, self.db, self.user_id)
            dialog.add_to_cart.connect(self.add_to_cart)
            dialog.recipe_updated.connect(self.load_recipes)
            dialog.recipe_deleted.connect(self.on_recipe_deleted)
            dialog.exec()
        except Exception as e:
            print(f"Ошибка при просмотре рецепта: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при просмотре рецепта: {e}")

    def on_recipe_deleted(self, recipe_id):
        """Обработчик удаления рецепта."""
        self.load_recipes()
        self.update_profile()
        QMessageBox.information(self, "Успех", "Рецепт успешно удален!")

    def add_to_cart(self, ingredients):
        """Добавляет ингредиенты в корзину."""
        if hasattr(self, 'cart_widget'):
            self.cart_widget.add_to_cart(ingredients)

    def export_cart(self):
        """Экспортирует список покупок в текстовый файл."""
        if hasattr(self, 'cart_widget'):
            self.cart_widget.export_cart()

    def update_stats(self):
        """Обновление статистики (псевдоним для update_profile)."""
        self.update_profile()

    def resizeEvent(self, event):
        """Обработчик события изменения размера окна."""
        super().resizeEvent(event)

        # При изменении размера окна обновляем FlowLayout
        if hasattr(self, 'current_recipe_cards') and self.current_recipe_cards:
            # Перезагружаем рецепты для корректного перераспределения карточек
            QTimer.singleShot(100, self.load_recipes)