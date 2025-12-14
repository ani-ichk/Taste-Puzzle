from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QScrollArea, QMessageBox,
                             QFrame)
from PyQt6.QtCore import Qt


class ProfileRecipeCard(QFrame):
    """Виджет карточки рецепта для отображения в профиле пользователя"""

    def __init__(self, recipe_data, db, parent_window=None):
        super().__init__()
        self.recipe_data = recipe_data
        self.db = db
        self.parent_window = parent_window
        self.user_id = None

        # Получаем user_id из parent_window разными способами
        if parent_window:
            if hasattr(parent_window, 'user_id'):
                # Если это MainWindow
                self.user_id = parent_window.user_id
            elif hasattr(parent_window, 'main_window') and hasattr(parent_window.main_window, 'user_id'):
                # Если это ProfileWidget
                self.user_id = parent_window.main_window.user_id

        self.init_ui()

    def init_ui(self):
        """Инициализация пользовательского интерфейса карточки профиля"""
        self.setFixedSize(180, 220)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: none;
                border-radius: 10px;
                margin: 5px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
                transition: all 0.2s ease;
            }
            QFrame:hover {
                box-shadow: 0 4px 15px rgba(52, 152, 219, 0.12);
                transform: translateY(-2px);
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Контейнер для изображения
        image_container = QWidget()
        image_container.setFixedHeight(120)
        image_container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f5f7fa, stop:1 #e4e7eb);
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border-bottom: 1px solid #e9ecef;
            }
        """)

        image_layout = QVBoxLayout(image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.load_image()
        image_layout.addWidget(self.image_label)
        layout.addWidget(image_container)

        # Контейнер для информации
        info_container = QWidget()
        info_container.setStyleSheet("background-color: white;")
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(12, 12, 12, 12)
        info_layout.setSpacing(8)

        # Название рецепта
        self.name_label = QLabel(self.recipe_data[2] if len(self.recipe_data) > 2 else "Без названия")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: 500;
                color: #2c3e50;
                line-height: 1.3;
            }
        """)
        self.name_label.setWordWrap(True)
        self.name_label.setMaximumHeight(40)
        info_layout.addWidget(self.name_label)

        # Контейнер для статусов
        self.status_container = QWidget()
        self.status_container.setFixedHeight(20)
        self.status_layout = QHBoxLayout(self.status_container)
        self.status_layout.setContentsMargins(0, 0, 0, 0)
        self.status_layout.setSpacing(5)

        self.update_status_icons()
        self.status_layout.addStretch()
        info_layout.addWidget(self.status_container)

        layout.addWidget(info_container)
        self.setLayout(layout)

    def load_image(self):
        """Загружает изображение рецепта"""
        recipe_id = self.recipe_data[0] if len(self.recipe_data) > 0 else None
        if recipe_id:
            pixmap = self.db.get_recipe_image(recipe_id)
            if pixmap and not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(178, 118, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                              Qt.TransformationMode.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
                self.image_label.setScaledContents(True)
                return

        # Если нет изображения, показываем иконку
        self.image_label.setText("🍳")
        self.image_label.setStyleSheet("font-size: 32px; color: #6c757d;")

    def update_status_icons(self):
        """Обновляет иконки статусов"""
        # Очищаем предыдущие иконки
        while self.status_layout.count():
            item = self.status_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Проверяем статусы рецепта
        is_cooked = len(self.recipe_data) > 16 and self.recipe_data[16]
        is_favorite = self.recipe_data[15] if len(self.recipe_data) > 15 else False

        if is_cooked:
            cooked_icon = QLabel("✅")
            cooked_icon.setStyleSheet("font-size: 10px;")
            self.status_layout.addWidget(cooked_icon)

        if is_favorite:
            favorite_icon = QLabel("❤️")
            favorite_icon.setStyleSheet("font-size: 10px;")
            self.status_layout.addWidget(favorite_icon)

    def mouseDoubleClickEvent(self, event):
        """Обработчик двойного клика по карточке"""
        view_recipe_target = None

        if hasattr(self.parent_window, 'view_recipe'):
            view_recipe_target = self.parent_window
        elif hasattr(self.parent_window, 'main_window') and hasattr(self.parent_window.main_window, 'view_recipe'):
            view_recipe_target = self.parent_window.main_window

        if view_recipe_target:
            view_recipe_target.view_recipe(self.recipe_data)
        else:
            print("Не удалось найти метод view_recipe")

    def update_data(self, new_recipe_data):
        """Обновляет данные карточки"""
        self.recipe_data = new_recipe_data
        self.name_label.setText(self.recipe_data[2] if len(self.recipe_data) > 2 else "Без названия")
        self.update_status_icons()
        self.load_image()


class ProfileWidget(QWidget):
    """Виджет профиля пользователя"""

    def __init__(self, db, user_id, main_window):
        super().__init__()
        self.db = db
        self.user_id = user_id
        self.main_window = main_window

        self.init_ui()
        self.update_profile()

    def init_ui(self):
        """Инициализация пользовательского интерфейса профиля"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Информация о пользователе
        self.profile_info = QLabel()
        self.profile_info.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #495057;
                background-color: white;
                padding: 15px;
                border-radius: 8px;
                border: 1px solid #dee2e6;
                min-height: 60px;
            }
        """)
        self.profile_info.setWordWrap(True)
        layout.addWidget(self.profile_info)

        stats_group = QLabel("📊 Статистика")
        stats_group.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
            margin-top: 20px;
        """)
        layout.addWidget(stats_group)

        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #495057;
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                border: 1px solid #dee2e6;
                min-height: 120px;
            }
        """)
        self.stats_label.setWordWrap(True)
        layout.addWidget(self.stats_label)

        favorites_label = QLabel("❤️ Избранные рецепты")
        favorites_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #2c3e50;
            margin-top: 20px;
            padding-bottom: 8px;
            border-bottom: 2px solid #e9ecef;
        """)
        layout.addWidget(favorites_label)

        self.favorites_scroll = QScrollArea()
        self.favorites_widget = QWidget()
        self.favorites_layout = QHBoxLayout(self.favorites_widget)
        self.favorites_layout.setSpacing(10)
        self.favorites_layout.setContentsMargins(15, 10, 15, 10)
        self.favorites_layout.addStretch(1)

        self.favorites_scroll.setWidget(self.favorites_widget)
        self.favorites_scroll.setWidgetResizable(True)
        self.favorites_scroll.setFixedHeight(270)
        self.favorites_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #dee2e6;
                border-radius: 8px;
                background-color: #f8f9fa;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)
        layout.addWidget(self.favorites_scroll)

        cooked_label = QLabel("✅ Приготовленные рецепты")
        cooked_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #2c3e50;
            margin-top: 20px;
            padding-bottom: 8px;
            border-bottom: 2px solid #e9ecef;
        """)
        layout.addWidget(cooked_label)

        self.cooked_scroll = QScrollArea()
        self.cooked_widget = QWidget()
        self.cooked_layout = QHBoxLayout(self.cooked_widget)
        self.cooked_layout.setSpacing(10)
        self.cooked_layout.setContentsMargins(15, 10, 15, 10)
        self.cooked_layout.addStretch(1)

        self.cooked_scroll.setWidget(self.cooked_widget)
        self.cooked_scroll.setWidgetResizable(True)
        self.cooked_scroll.setFixedHeight(270)
        self.cooked_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #dee2e6;
                border-radius: 8px;
                background-color: #f8f9fa;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)
        layout.addWidget(self.cooked_scroll)

        logout_layout = QHBoxLayout()
        logout_btn = QPushButton("🚪 Выйти из аккаунта")
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        logout_btn.clicked.connect(self.logout)
        logout_layout.addWidget(logout_btn)
        logout_layout.addStretch()
        layout.addLayout(logout_layout)

        layout.addStretch()

        self.setLayout(layout)

    def update_profile(self):
        """Обновляет данные профиля пользователя"""
        try:
            # Загружаем данные профиля из базы данных
            profile_data = self.db.get_user_profile(self.user_id)
            if profile_data:
                profile_text = f"""
                    <div style="text-align: center; padding: 10px;">
                        <h2 style="margin: 0; color: #2c3e50;">👤 {profile_data['login']}</h2>
                    </div>
                    """
                self.profile_info.setText(profile_text)

                stats_text = f"""
                    <b>📊 Ваша статистика:</b><br><br>
                    📖 <b>Всего рецептов:</b> {profile_data['recipes_count']}<br>
                    ❤️ <b>В избранном:</b> {profile_data['favorites_count']}<br>
                    ✅ <b>Приготовлено:</b> {profile_data['cooked_count']}<br>
                    🛒 <b>В корзине:</b> {profile_data['cart_count']}<br>
                    """
                self.stats_label.setText(stats_text)

            self.load_favorite_recipes()
            self.load_cooked_recipes()

        except Exception as e:
            print(f"Ошибка при обновлении профиля: {e}")

    def load_favorite_recipes(self):
        """Загружает избранные рецепты пользователя"""
        # Очищаем предыдущие карточки избранных рецептов
        for i in reversed(range(self.favorites_layout.count())):
            item = self.favorites_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()

        try:
            favorite_recipes = self.db.get_favorite_recipes(self.user_id)
            if favorite_recipes:
                for recipe in favorite_recipes:
                    card = ProfileRecipeCard(recipe, self.db, self)
                    self.favorites_layout.addWidget(card)
            else:
                no_favorites_label = QLabel("Нет избранных рецептов")
                no_favorites_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_favorites_label.setStyleSheet("color: #6c757d; font-size: 14px; padding: 40px;")
                self.favorites_layout.addWidget(no_favorites_label)
        except Exception as e:
            print(f"Ошибка при загрузке избранных рецептов: {e}")

    def load_cooked_recipes(self):
        """Загружает приготовленные рецепты пользователя"""
        # Очищаем предыдущие карточки приготовленных рецептов
        for i in reversed(range(self.cooked_layout.count())):
            item = self.cooked_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        try:
            cooked_recipes = self.db.get_cooked_recipes(self.user_id)
            if cooked_recipes:
                for recipe in cooked_recipes:
                    card = ProfileRecipeCard(recipe, self.db, self)
                    self.cooked_layout.addWidget(card)
            else:
                no_cooked_label = QLabel("Нет приготовленных рецептов")
                no_cooked_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_cooked_label.setStyleSheet("color: #6c757d; font-size: 14px; padding: 40px;")
                self.cooked_layout.addWidget(no_cooked_label)
        except Exception as e:
            print(f"Ошибка при загрузке приготовленных рецептов: {e}")

    def logout(self):
        """Обрабатывает выход пользователя из аккаунта с подтверждением"""
        reply = QMessageBox.question(
            self,
            "Подтверждение выхода",
            "Вы действительно хотите выйти из аккаунта?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.main_window and hasattr(self.main_window, 'logout_callback'):
                self.main_window.logout_callback()