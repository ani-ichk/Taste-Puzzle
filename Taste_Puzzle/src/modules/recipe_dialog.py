import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLineEdit, QTextEdit, QComboBox, QSpinBox,
                             QPushButton, QLabel, QMessageBox, QFileDialog, QScrollArea, QTableWidget, QTableWidgetItem,
                             QHeaderView, QDoubleSpinBox, QWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon

from src.database import Recipe


class ClickableLabel(QLabel):
    """Метка с кликабельной ссылкой"""
    clicked = pyqtSignal()

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("color: #0066cc; text-decoration: underline;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class RecipeDialog(QDialog):
    """Класс диалога для добавления и редактирования рецептов"""

    # Сигнал, испускаемый при сохранении рецепта
    recipe_saved = pyqtSignal()

    def __init__(self, db, user_id, recipe_data=None):
        """Конструктор диалога рецепта"""
        super().__init__()
        self.db = db
        self.user_id = user_id
        self.recipe_data = recipe_data
        self.ingredients_data = []
        self.image_data = None
        self.temp_image_path = None

        self.init_ui()
        if self.recipe_data:
            self.load_recipe_data()

    def format_instructions(self, instructions):
        """Форматирует инструкции с автоматической нумерацией и улучшенным видом"""
        if not instructions:
            return "Инструкции отсутствуют"

        # Разделение инструкций по строкам
        steps = instructions.split('\n')
        numbered_steps = []

        # Нумерация каждого шага
        for i, step in enumerate(steps, 1):
            step = step.strip()
            if step:
                # Убираем существующую нумерацию если есть
                if step and step[0].isdigit() and '.' in step.split()[0]:
                    step = step.split('.', 1)[1].strip()
                numbered_steps.append(f"{i}. {step}")

        if not numbered_steps:
            return "Инструкции отсутствуют"

        return '\n\n'.join(numbered_steps)  # Двойной перенос между шагами

    def unformat_instructions(self, instructions):
        """Убирает автоматическую нумерацию для сохранения в базу"""
        if not instructions:
            return ""

        steps = instructions.split('\n')
        unnumbered_steps = []

        for step in steps:
            step = step.strip()
            if step:
                # Убираем нумерацию (формат "1. Текст")
                if step[0].isdigit() and '.' in step.split()[0]:
                    step = step.split('.', 1)[1].strip()
                unnumbered_steps.append(step)

        return '\n'.join(unnumbered_steps)

    def init_ui(self):
        """Метод инициализации пользовательского интерфейса"""
        layout = QVBoxLayout()

        self.setWindowIcon(QIcon("img/icon.ico"))

        self.setStyleSheet("""
            QDialog {
                background-color: #f5f7fa;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #2c3e50;
                font-weight: 500;
            }
            QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
                font-size: 14px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton#image_btn {
                background-color: #95a5a6;
            }
            QPushButton#image_btn:hover {
                background-color: #7f8c8d;
            }
            QTableWidget {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #ecf0f1;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)

        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # ФОРМА ДЛЯ ОСНОВНОЙ ИНФОРМАЦИИ О РЕЦЕПТЕ
        form_layout = QFormLayout()
        form_layout.setContentsMargins(10, 10, 10, 10)

        # Создание элементов ввода
        self.name_input = QLineEdit()
        self.name_input.setStyleSheet("font-size: 16px; font-weight: bold;")

        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)

        self.instruction_input = QTextEdit()
        self.instruction_input.setMaximumHeight(150)
        self.instruction_input.setPlaceholderText("Каждая новая строка будет автоматически пронумерована")

        self.cook_time_input = QSpinBox()
        self.cook_time_input.setRange(1, 480)
        self.cook_time_input.setSuffix(' мин')

        self.servings_input = QSpinBox()
        self.servings_input.setRange(1, 20)
        self.servings_input.setValue(4)
        self.servings_input.setSuffix(' порции')

        self.video_url_input = QLineEdit()
        self.video_url_input.setPlaceholderText("Ссылка на видео (YouTube, Vimeo и т.д.)")

        # === ВЫПАДАЮЩИЙ СПИСОК ТИПА БЛЮДА ===
        self.dish_type_combo = QComboBox()
        self.dish_type_combo.addItem("Не выбран", None)
        dish_types = self.db.get_dish_types()
        for dish_type_id, dish_type_name in dish_types:
            self.dish_type_combo.addItem(dish_type_name, dish_type_id)

        # === ВЫПАДАЮЩИЙ СПИСОК КУХНИ ===
        self.cuisine_combo = QComboBox()
        self.cuisine_combo.addItem("Не выбрана", None)
        cuisines = self.db.get_cuisines()
        for cuisine_id, cuisine_name in cuisines:
            self.cuisine_combo.addItem(cuisine_name, cuisine_id)

        # СЕКЦИЯ ЗАГРУЗКИ ИЗОБРАЖЕНИЯ
        image_layout = QHBoxLayout()
        self.image_label = QLabel()
        self.image_label.setFixedSize(150, 150)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #bdc3c7;
                border-radius: 8px;
                background-color: #ecf0f1;
                color: #7f8c8d;
            }
        """)
        self.image_label.setText("Изображение\nне выбрано")

        load_image_btn = QPushButton("Выбрать изображение")
        load_image_btn.setObjectName("image_btn")
        load_image_btn.clicked.connect(self.load_image)

        image_layout.addWidget(self.image_label)
        image_layout.addWidget(load_image_btn)

        # ДОБАВЛЕНИЕ ЭЛЕМЕНТОВ В ФОРМУ
        form_layout.addRow('Название:', self.name_input)
        form_layout.addRow('Описание:', self.description_input)
        form_layout.addRow('Кухня:', self.cuisine_combo)
        form_layout.addRow('Тип блюда:', self.dish_type_combo)
        form_layout.addRow('Время приготовления:', self.cook_time_input)
        form_layout.addRow('Количество порций:', self.servings_input)
        form_layout.addRow('Видео-ссылка:', self.video_url_input)
        form_layout.addRow('Изображение:', image_layout)
        form_layout.addRow('Инструкции:', self.instruction_input)

        # СЕКЦИЯ ДЛЯ РАБОТЫ С ИНГРЕДИЕНТАМИ
        ingredients_layout = QVBoxLayout()
        ingredients_layout.addWidget(QLabel('Ингредиенты:'))

        # Панель добавления ингредиентов
        add_ingredient_layout = QHBoxLayout()

        self.ingredient_combo = QComboBox()
        ingredients = self.db.get_ingredients()  # Возвращает список кортежей (id, name)
        for ingredient_id, ingredient_name in ingredients:
            self.ingredient_combo.addItem(ingredient_name, ingredient_id)

        # Спинбокс для количества
        self.quantity_input = QDoubleSpinBox()
        self.quantity_input.setRange(0.1, 10000)
        self.quantity_input.setDecimals(2)
        self.quantity_input.setValue(100)
        self.quantity_input.setSingleStep(10)

        self.unit_combo = QComboBox()
        units = ["г", "кг", "мл", "л", "шт", "ст.л.", "ч.л.", "стакан", "щепотка", "по вкусу"]
        self.unit_combo.addItems(units)

        add_ingredient_btn = QPushButton('Добавить')
        add_ingredient_btn.clicked.connect(self.add_ingredient)

        add_ingredient_layout.addWidget(QLabel('Ингредиент:'))
        add_ingredient_layout.addWidget(self.ingredient_combo)
        add_ingredient_layout.addWidget(QLabel("Количество:"))
        add_ingredient_layout.addWidget(self.quantity_input)
        add_ingredient_layout.addWidget(self.unit_combo)
        add_ingredient_layout.addWidget(add_ingredient_btn)

        self.ingredients_table = QTableWidget()
        self.ingredients_table.setColumnCount(3)
        self.ingredients_table.setHorizontalHeaderLabels(["Ингредиент", "Количество", "Единица"])
        self.ingredients_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        remove_ingredient_btn = QPushButton('Удалить выбранный')
        remove_ingredient_btn.clicked.connect(self.remove_ingredient)

        ingredients_layout.addLayout(add_ingredient_layout)
        ingredients_layout.addWidget(self.ingredients_table)
        ingredients_layout.addWidget(remove_ingredient_btn)

        # СЕКЦИЯ ДЛЯ КБЖУ
        kbju_layout = QHBoxLayout()
        kbju_layout.addWidget(QLabel('Пищевая ценность:'))

        self.calories_input = QSpinBox()
        self.calories_input.setRange(0, 5000)
        self.calories_input.setPrefix("Калории: ")
        self.calories_input.setSuffix(" ккал")

        self.proteins_input = QDoubleSpinBox()
        self.proteins_input.setRange(0, 200)
        self.proteins_input.setPrefix("Белки: ")
        self.proteins_input.setSuffix(" г")

        self.fats_input = QDoubleSpinBox()
        self.fats_input.setRange(0, 200)
        self.fats_input.setPrefix("Жиры: ")
        self.fats_input.setSuffix(" г")

        self.carbs_input = QDoubleSpinBox()
        self.carbs_input.setRange(0, 200)
        self.carbs_input.setPrefix("Углеводы: ")
        self.carbs_input.setSuffix(" г")

        kbju_layout.addWidget(self.calories_input)
        kbju_layout.addWidget(self.proteins_input)
        kbju_layout.addWidget(self.fats_input)
        kbju_layout.addWidget(self.carbs_input)
        kbju_layout.addStretch()

        # ПАНЕЛЬ КНОПОК УПРАВЛЕНИЯ
        buttons_layout = QHBoxLayout()
        save_btn = QPushButton('Сохранить')
        save_btn.clicked.connect(self.save_recipe)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)

        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)

        scroll_layout.addLayout(form_layout)
        scroll_layout.addLayout(ingredients_layout)
        scroll_layout.addLayout(kbju_layout)
        scroll_layout.addLayout(buttons_layout)

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        self.setLayout(layout)
        self.setWindowTitle('Редактировать рецепт' if self.recipe_data else 'Новый рецепт')
        self.resize(800, 850)

    def load_image(self):
        """Загрузка изображения для рецепта"""
        try:
            file_name, _ = QFileDialog.getOpenFileName(
                self,
                "Выберите изображение",
                "",
                "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
            )

            if file_name:
                # Размер файла (максимум 5 МБ)
                file_size = os.path.getsize(file_name)
                if file_size > 5 * 1024 * 1024:
                    QMessageBox.warning(self, "Ошибка", "Файл слишком большой (макс. 5 МБ)")
                    return

                # Оригинальный путь к файлу
                self.image_data = file_name

                # Показываем превью
                pixmap = QPixmap(file_name)
                if not pixmap.isNull():
                    # Масштабируем для отображения в метке
                    scaled_pixmap = pixmap.scaled(
                        140, 140,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.image_label.setPixmap(scaled_pixmap)
                    self.image_label.setText("")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки изображения: {str(e)}")

    def add_ingredient(self):
        # Метод добавления ингредиента в таблицу
        try:
            ing_id = self.ingredient_combo.currentData()
            ing_name = self.ingredient_combo.currentText()
            quantity = self.quantity_input.value()
            unit = self.unit_combo.currentText()

            # Проверка количества
            if quantity <= 0:
                QMessageBox.warning(self, 'Ошибка', 'Введите количество больше 0')
                return

            # Проверка на дубликаты
            for existing_ing in self.ingredients_data:
                if existing_ing[0] == ing_id:
                    QMessageBox.warning(self, 'Ошибка', 'Этот ингредиент уже добавлен')
                    return

            self.ingredients_data.append((ing_id, quantity, unit))

            # Добавление ингредиента в таблицу
            row = self.ingredients_table.rowCount()
            self.ingredients_table.insertRow(row)
            self.ingredients_table.setItem(row, 0, QTableWidgetItem(ing_name))
            self.ingredients_table.setItem(row, 1, QTableWidgetItem(str(quantity)))
            self.ingredients_table.setItem(row, 2, QTableWidgetItem(unit))

            # Очистка полей ввода
            self.quantity_input.setValue(100)

        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка при добавлении ингредиента: {e}')

    def remove_ingredient(self):
        # Метод удаления выбранного ингредиента из таблицы
        try:
            current_row = self.ingredients_table.currentRow()
            if current_row >= 0:
                self.ingredients_data.pop(current_row)
                self.ingredients_table.removeRow(current_row)
            else:
                QMessageBox.warning(self, 'Ошибка', 'Выберите ингредиент для удаления')
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка при удалении ингредиента: {e}')

    def load_recipe_data(self):
        # Метод загрузки данных рецепта в форму (для редактирования)
        try:
            # Получаем ID рецепта
            recipe_id = None
            if isinstance(self.recipe_data, int):
                recipe_id = self.recipe_data
            elif self.recipe_data and isinstance(self.recipe_data, tuple) and len(self.recipe_data) > 0:
                recipe_id = self.recipe_data[0]
            else:
                return

            # Получаем рецепт из базы
            session = self.db.Session()
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()

            if not recipe:
                QMessageBox.warning(self, 'Ошибка', 'Рецепт не найден')
                session.close()
                return

            # Загрузка основных данных рецепта
            self.name_input.setText(recipe.name)
            self.description_input.setPlainText(recipe.description or '')

            # Форматируем инструкции с автоматической нумерацией
            instructions = self.format_instructions(recipe.instruction or '')
            self.instruction_input.setPlainText(instructions)

            self.cook_time_input.setValue(recipe.cook_time or 30)
            self.servings_input.setValue(recipe.servings or 4)

            # Загрузка видео-ссылки
            if recipe.external_url:
                self.video_url_input.setText(recipe.external_url)

            # Загрузка кухни
            if recipe.cuisine_id:
                for i in range(self.cuisine_combo.count()):
                    if self.cuisine_combo.itemData(i) == recipe.cuisine_id:
                        self.cuisine_combo.setCurrentIndex(i)
                        break

            # Загрузка типа блюда
            if recipe.dish_type_id:
                for i in range(self.dish_type_combo.count()):
                    if self.dish_type_combo.itemData(i) == recipe.dish_type_id:
                        self.dish_type_combo.setCurrentIndex(i)
                        break

            # Загрузка изображения если есть
            if recipe.image:
                # get_recipe_image возвращает QPixmap
                pixmap = self.db.get_recipe_image(recipe.id)
                if pixmap and not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(140, 140,
                                                  Qt.AspectRatioMode.KeepAspectRatio,
                                                  Qt.TransformationMode.SmoothTransformation)
                    self.image_label.setPixmap(scaled_pixmap)
                    self.image_label.setText("")
                    # Сохраняем путь к изображению для возможного пересохранения
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    project_root = os.path.dirname(current_dir)
                    image_path = os.path.join(project_root, 'img', 'recipe_img', recipe.image)
                    if os.path.exists(image_path):
                        self.image_data = image_path

            ingredients = self.db.get_recipe_ingredients(recipe.id)
            for ing in ingredients:  # ing - это кортеж (name, quantity, unit)
                # Находим ID ингредиента по названию
                ing_id = None
                for ing_tuple in self.db.get_ingredients():
                    if ing_tuple[1] == ing[0]:  # ing[0] - название ингредиента
                        ing_id = ing_tuple[0]
                        break

                if ing_id:
                    quantity = ing[1]
                    unit = ing[2]
                    self.ingredients_data.append((ing_id, quantity, unit))

                    # Добавление в таблицу
                    row = self.ingredients_table.rowCount()
                    self.ingredients_table.insertRow(row)
                    self.ingredients_table.setItem(row, 0, QTableWidgetItem(ing[0]))
                    self.ingredients_table.setItem(row, 1, QTableWidgetItem(str(quantity)))
                    self.ingredients_table.setItem(row, 2, QTableWidgetItem(unit))

            # Загрузка данных КБЖУ
            if recipe.nutrition:
                self.calories_input.setValue(recipe.nutrition.calories or 0)
                self.proteins_input.setValue(recipe.nutrition.proteins or 0)
                self.fats_input.setValue(recipe.nutrition.fats or 0)
                self.carbs_input.setValue(recipe.nutrition.carbohydrates or 0)

            session.close()

        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка при загрузке данных рецепта: {e}')

    def is_valid_url(self, url):
        """Проверяет, является ли строка валидным URL для видео"""
        import re

        if not url:
            return True

        # Проверяем общий формат URL
        url_pattern = re.compile(
            r'^(https?://)?'  # протокол
            r'(([A-Z0-9][A-Z0-9_-]*)(\.[A-Z0-9][A-Z0-9_-]*)+)'  # домен
            r'(:\d+)?'  # порт
            r'(/.*)?$', re.IGNORECASE)

        if not url_pattern.match(url):
            return False

        # Проверяем популярные видео-платформы
        video_domains = [
            'youtube.com', 'youtu.be',
            'vimeo.com',
            'dailymotion.com',
            'rutube.ru'
        ]

        url_lower = url.lower()
        for domain in video_domains:
            if domain in url_lower:
                return True

        return True

    def save_recipe(self):
        """Метод сохранения рецепта"""
        try:
            # Проверка обязательных полей
            if not self.name_input.text().strip():
                QMessageBox.warning(self, 'Ошибка', 'Введите название рецепта')
                return

            if not self.ingredients_data:
                QMessageBox.warning(self, 'Ошибка', 'Добавьте хотя бы один ингредиент')
                return

            # Получение данных из формы
            dish_type_id = self.dish_type_combo.currentData()
            cuisine_id = self.cuisine_combo.currentData()

            # Проверка типа блюда
            if not dish_type_id:
                QMessageBox.warning(self, 'Ошибка', 'Выберите тип блюда')
                return

            # Убираем автоматическую нумерацию перед сохранением
            instructions = self.unformat_instructions(self.instruction_input.toPlainText())

            # Получаем видео-ссылку
            video_url = self.video_url_input.text().strip()
            if video_url and not self.is_valid_url(video_url):
                reply = QMessageBox.question(
                    self,
                    'Некорректная ссылка',
                    'Введенная видео-ссылка может быть некорректной. Сохранить как есть?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return

            # Формируем данные КБЖУ
            nutrition_data = (
                self.calories_input.value(),
                self.proteins_input.value(),
                self.fats_input.value(),
                self.carbs_input.value()
            )

            # Формируем ингредиенты в правильном формате для БД
            ingredients_list = []
            for ing_id, quantity, unit in self.ingredients_data:
                # Находим название ингредиента для логов
                ing_name = ""
                for i in range(self.ingredient_combo.count()):
                    if self.ingredient_combo.itemData(i) == ing_id:
                        ing_name = self.ingredient_combo.itemText(i)
                        break

                ingredients_list.append((ing_id, quantity, unit))

            # Обработка изображения
            image_data = self.image_data

            # Сохранение рецепта в базу данных
            recipe_id = None

            servings = self.servings_input.value()

            if self.recipe_data:
                # Режим редактирования
                if isinstance(self.recipe_data, int):
                    recipe_id = self.recipe_data
                else:
                    recipe_id = self.recipe_data[0]

                # Обновляем рецепт
                success = self.db.update_recipe(
                    recipe_id=recipe_id,
                    name=self.name_input.text(),
                    instruction=instructions,
                    description=self.description_input.toPlainText(),
                    dish_type_id=dish_type_id,
                    cuisine_id=cuisine_id,
                    cook_time=self.cook_time_input.value(),
                    ingredients_list=ingredients_list,
                    nutrition_data=nutrition_data,
                    image=image_data
                )

                # Обновляем дополнительные поля
                if success:
                    session = self.db.Session()
                    try:
                        recipe = session.query(Recipe).filter_by(id=recipe_id).first()
                        if recipe:
                            recipe.servings = servings
                            recipe.external_url = video_url
                            session.commit()
                            print("Дополнительные поля обновлены")
                    except Exception as e:
                        print(f"Ошибка обновления доп. полей: {e}")
                    finally:
                        session.close()

            else:
                # Режим добавления нового рецепта
                recipe_id = self.db.add_recipe(
                    user_id=self.user_id,
                    name=self.name_input.text(),
                    instruction=instructions,
                    description=self.description_input.toPlainText(),
                    dish_type_id=dish_type_id,
                    cuisine_id=cuisine_id,
                    cook_time=self.cook_time_input.value(),
                    ingredients_list=ingredients_list,
                    nutrition_data=nutrition_data,
                    image=image_data
                )
                success = recipe_id is not None

                # Обновляем дополнительные поля
                if success:
                    session = self.db.Session()
                    try:
                        recipe = session.query(Recipe).filter_by(id=recipe_id).first()
                        if recipe:
                            recipe.servings = servings
                            recipe.external_url = video_url
                            session.commit()
                    except Exception as e:
                        print(f"Ошибка добавления доп. полей: {e}")
                    finally:
                        session.close()

            if success:
                print("✅ РЕЦЕПТ УСПЕШНО СОХРАНЕН!")

                # Очищаем временные файлы если есть
                if self.temp_image_path and os.path.exists(self.temp_image_path):
                    try:
                        os.remove(self.temp_image_path)
                    except Exception as e:
                        print(f"Не удалось удалить временный файл: {e}")

                self.recipe_saved.emit()
                self.accept()
                QMessageBox.information(self, 'Успех', 'Рецепт успешно сохранен!')
            else:
                QMessageBox.warning(self, 'Ошибка', 'Не удалось сохранить рецепт')

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, 'Ошибка', f'Ошибка при сохранении рецепта:\n{str(e)}')

    def closeEvent(self, event):
        """Очистка временных файлов при закрытии диалога"""
        if self.temp_image_path and os.path.exists(self.temp_image_path):
            try:
                os.remove(self.temp_image_path)
            except:
                pass
        super().closeEvent(event)


class RecipeCardDialog(QDialog):
    """Класс диалога для просмотра рецепта в виде карточки"""
    recipe_updated = pyqtSignal()
    recipe_deleted = pyqtSignal(int)
    add_to_cart = pyqtSignal(list)

    def __init__(self, recipe_data, db, user_id):
        super().__init__()
        self.db = db
        self.user_id = user_id

        # Получаем объект рецепта по ID
        if isinstance(recipe_data, int):
            self.recipe_id = recipe_data
        elif isinstance(recipe_data, tuple) and len(recipe_data) > 0:
            self.recipe_id = recipe_data[0]
        else:
            QMessageBox.warning(None, 'Ошибка', 'Некорректные данные рецепта')
            self.reject()
            return

        # Используем прямой запрос к сессии
        session = self.db.Session()
        try:
            from sqlalchemy.orm import joinedload

            self.recipe = session.query(Recipe).options(
                joinedload(Recipe.cuisine),
                joinedload(Recipe.dish_type),
                joinedload(Recipe.nutrition)
            ).filter(Recipe.id == self.recipe_id).first()
        finally:
            session.close()

        if not self.recipe:
            QMessageBox.warning(None, 'Ошибка', 'Рецепт не найден')
            self.reject()
            return

        self.init_ui()

    def init_ui(self):
        self.setFixedSize(850, 950)
        self.setWindowTitle(self.recipe.name)

        # Установка иконки
        self.setWindowIcon(QIcon("../img/icon.ico"))

        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f8f9fa, stop: 1 #e9ecef);
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #2c3e50;
            }
            QTextEdit {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton {
                padding: 15px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 20px;
                margin: 5px;
                border: none;
                min-width: 60px;
                min-height: 60px;
            }
            QPushButton:hover {
                transform: scale(1.05);
            }
            QPushButton:pressed {
                transform: scale(0.95);
            }
            QPushButton#cart_btn {
                background-color: #28a745;
                color: white;
            }
            QPushButton#cart_btn:hover {
                background-color: #218838;
            }
            QPushButton#favorite_btn {
                background-color: #ffc107;
                color: #212529;
            }
            QPushButton#favorite_btn:hover {
                background-color: #e0a800;
            }
            QPushButton#cooked_btn {
                background-color: #17a2b8;
                color: white;
            }
            QPushButton#cooked_btn:hover {
                background-color: #138496;
            }
            QPushButton#edit_btn {
                background-color: #007bff;
                color: white;
            }
            QPushButton#edit_btn:hover {
                background-color: #0056b3;
            }
            QPushButton#delete_btn {
                background-color: #dc3545;
                color: white;
            }
            QPushButton#delete_btn:hover {
                background-color: #c82333;
            }
            .section-header {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin-top: 25px;
                margin-bottom: 10px;
                padding: 5px;
                background-color: white;
                border-radius: 6px;
                border-left: 4px solid #007bff;
            }
            .info-box {
                background-color: white;
                padding: 12px;
                border-radius: 8px;
                border: 1px solid #dee2e6;
                margin: 5px 0;
            }
        """)

        # Основной layout с прокруткой
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # === ПЕРВЫЙ БЛОК: Заголовок и основная информация ===
        title = QLabel(self.recipe.name)
        title.setStyleSheet("""
            QLabel {
                font-size: 26px;
                font-weight: bold;
                color: #2c3e50;
                padding: 20px;
                background-color: white;
                border-radius: 10px;
                text-align: center;
                border: 2px solid #dee2e6;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        layout.addWidget(title)

        # Блок с фото и информацией
        first_block_layout = QHBoxLayout()
        first_block_layout.setSpacing(20)

        # Фотография (слева)
        image_container = QVBoxLayout()
        image_label = QLabel()
        image_label.setFixedSize(220, 180)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px solid #dee2e6;
                border-radius: 10px;
            }
        """)

        pixmap = self.db.get_recipe_image(self.recipe.id)
        if pixmap and not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(210, 170, Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)
            image_label.setPixmap(scaled_pixmap)
        else:
            image_label.setText("🖼️\nНет\nизображения")
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            image_label.setStyleSheet(image_label.styleSheet() + "color: #6c757d; font-size: 12px;")

        image_container.addWidget(image_label)
        image_container.addStretch()

        # Информация справа
        info_container = QVBoxLayout()
        info_container.setSpacing(15)

        # Количество порций
        if self.recipe.servings:
            servings_box = QWidget()
            servings_box.setStyleSheet("""
                QWidget {
                    background-color: #e8f4fd;
                    border-radius: 8px;
                    border: 1px solid #c5e1fa;
                }
            """)
            servings_layout = QVBoxLayout(servings_box)
            servings_label = QLabel("🍽️ Количество порций")
            servings_label.setStyleSheet("font-weight: bold; color: #0d6efd; font-size: 14px; margin-bottom: 5px;")
            servings_value = QLabel(f"{self.recipe.servings} порций")
            servings_value.setStyleSheet("color: #0d6efd; font-size: 16px; font-weight: 500;")
            servings_layout.addWidget(servings_label)
            servings_layout.addWidget(servings_value)
            info_container.addWidget(servings_box)

        # Кухня
        if self.recipe.cuisine:
            cuisine_box = QWidget()
            cuisine_box.setStyleSheet("""
                QWidget {
                    background-color: #e8f5e9;
                    border-radius: 8px;
                    border: 1px solid #c8e6c9;
                }
            """)
            cuisine_layout = QVBoxLayout(cuisine_box)
            cuisine_label = QLabel("🌍 Кухня")
            cuisine_label.setStyleSheet("font-weight: bold; color: #2e7d32; font-size: 14px; margin-bottom: 5px;")
            cuisine_value = QLabel(self.recipe.cuisine.name)
            cuisine_value.setStyleSheet("color: #2e7d32; font-size: 16px; font-weight: 500;")
            cuisine_value.setWordWrap(True)
            cuisine_layout.addWidget(cuisine_label)
            cuisine_layout.addWidget(cuisine_value)
            info_container.addWidget(cuisine_box)

        # Категория
        if self.recipe.dish_type:
            category_box = QWidget()
            category_box.setStyleSheet("""
                QWidget {
                    background-color: #e3f2fd;
                    border-radius: 8px;
                    border: 1px solid #bbdefb;
                }
            """)
            category_layout = QVBoxLayout(category_box)
            category_label = QLabel("🍽️ Тип блюда")
            category_label.setStyleSheet("font-weight: bold; color: #1565c0; font-size: 14px; margin-bottom: 5px;")
            category_value = QLabel(self.recipe.dish_type.name)
            category_value.setStyleSheet("color: #1565c0; font-size: 16px; font-weight: 500;")
            category_value.setWordWrap(True)
            category_layout.addWidget(category_label)
            category_layout.addWidget(category_value)
            info_container.addWidget(category_box)

        # Время приготовления
        time_box = QWidget()
        time_box.setStyleSheet("""
            QWidget {
                background-color: #fff3e0;
                border-radius: 8px;
                border: 1px solid #ffe0b2;
            }
        """)
        time_layout = QVBoxLayout(time_box)
        time_label = QLabel("⏱️ Время приготовления")
        time_label.setStyleSheet("font-weight: bold; color: #ef6c00; font-size: 14px; margin-bottom: 5px;")
        time_value = QLabel(f"{self.recipe.cook_time or 'Не указано'} минут")
        time_value.setStyleSheet("color: #ef6c00; font-size: 16px; font-weight: 500;")
        time_layout.addWidget(time_label)
        time_layout.addWidget(time_value)
        info_container.addWidget(time_box)

        # Видео-ссылка
        if self.recipe.external_url:
            video_box = QWidget()
            video_box.setStyleSheet("""
                QWidget {
                    background-color: #f3e5f5;
                    border-radius: 8px;
                    border: 1px solid #e1bee7;
                }
            """)
            video_layout = QVBoxLayout(video_box)
            video_label = QLabel("🎬 Видео-рецепт")
            video_label.setStyleSheet("font-weight: bold; color: #7b1fa2; font-size: 14px; margin-bottom: 5px;")
            video_link = ClickableLabel(
                f'<a href="{self.recipe.external_url}" style="color: #7b1fa2; text-decoration: none; font-size: 14px;">Смотреть видео</a>')
            video_link.setOpenExternalLinks(True)
            video_link.clicked.connect(lambda: QMessageBox.information(self, "Видео", "Открываю видео-ссылку..."))
            video_layout.addWidget(video_label)
            video_layout.addWidget(video_link)
            info_container.addWidget(video_box)

        info_container.addStretch()

        first_block_layout.addLayout(image_container)
        first_block_layout.addLayout(info_container)
        layout.addLayout(first_block_layout)

        # Отступ между блоками
        layout.addSpacing(10)

        # === ВТОРОЙ БЛОК: Описание ===
        if self.recipe.description:
            description_label = QLabel("📝 Описание")
            description_label.setProperty("class", "section-header")
            layout.addWidget(description_label)

            description = QTextEdit()
            description.setPlainText(self.recipe.description)
            description.setReadOnly(True)
            description.setFixedHeight(100)
            description.setStyleSheet("""
                QTextEdit {
                    font-size: 14px; 
                    color: #495057; 
                    padding: 15px;
                    background-color: white;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    line-height: 1.4;
                }
            """)
            layout.addWidget(description)

        # === ТРЕТИЙ БЛОК: Ингредиенты ===
        ingredients_label = QLabel("🛒 Ингредиенты")
        ingredients_label.setProperty("class", "section-header")
        layout.addWidget(ingredients_label)

        ingredients_text = QTextEdit()
        ingredients_text.setReadOnly(True)
        ingredients_text.setFixedHeight(150)
        ingredients_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                font-size: 14px;
                line-height: 1.6;
            }
        """)

        try:
            ingredients = self.db.get_recipe_ingredients(self.recipe.id)
            ingredients_list = ""
            for ing in ingredients:
                # ing - это кортеж (name, quantity, unit)
                ingredients_list += f"• {ing[0]}: {ing[1]} {ing[2]}\n"
            ingredients_text.setPlainText(ingredients_list)
        except Exception as e:
            ingredients_text.setPlainText("Не удалось загрузить ингредиенты")

        layout.addWidget(ingredients_text)

        # === ЧЕТВЕРТЫЙ БЛОК: Инструкции ===
        instructions_label = QLabel("📋 Инструкции")
        instructions_label.setProperty("class", "section-header")
        layout.addWidget(instructions_label)

        instructions_text = QTextEdit()
        instructions_text.setReadOnly(True)
        instructions_text.setFixedHeight(200)
        instructions_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                font-size: 14px;
                line-height: 1.6;
            }
        """)

        formatted_instructions = self.format_instructions(self.recipe.instruction)
        instructions_text.setPlainText(formatted_instructions)
        layout.addWidget(instructions_text)

        # === ПЯТЫЙ БЛОК: КБЖУ ===
        if self.recipe.nutrition and any([
            self.recipe.nutrition.calories,
            self.recipe.nutrition.proteins,
            self.recipe.nutrition.fats,
            self.recipe.nutrition.carbohydrates
        ]):
            nutrition_label = QLabel("📊 Пищевая ценность (на порцию)")
            nutrition_label.setProperty("class", "section-header")
            layout.addWidget(nutrition_label)

            nutrition_box = QWidget()
            nutrition_box.setStyleSheet("""
                QWidget {
                    background-color: white;
                    border-radius: 10px;
                    padding: 15px;
                    border: 2px solid #dee2e6;
                }
            """)
            nutrition_layout = QHBoxLayout(nutrition_box)

            if self.recipe.nutrition.calories:
                calories_label = QLabel(f"🔥 {self.recipe.nutrition.calories} ккал")
                calories_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #dc3545;")
                nutrition_layout.addWidget(calories_label)

            if self.recipe.nutrition.proteins:
                proteins_label = QLabel(f"🥩 {self.recipe.nutrition.proteins} г белков")
                proteins_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #0d6efd;")
                nutrition_layout.addWidget(proteins_label)

            if self.recipe.nutrition.fats:
                fats_label = QLabel(f"🥑 {self.recipe.nutrition.fats} г жиров")
                fats_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffc107;")
                nutrition_layout.addWidget(fats_label)

            if self.recipe.nutrition.carbohydrates:
                carbs_label = QLabel(f"🍚 {self.recipe.nutrition.carbohydrates} г углеводов")
                carbs_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #198754;")
                nutrition_layout.addWidget(carbs_label)

            nutrition_layout.addStretch()
            layout.addWidget(nutrition_box)

        # === ШЕСТОЙ БЛОК ===
        buttons_label = QLabel("⚡ Действия")
        buttons_label.setProperty("class", "section-header")
        layout.addWidget(buttons_label)

        buttons_container = QWidget()
        buttons_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 10px;
                padding: 10px;
                border: 1px solid #dee2e6;
            }
        """)

        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setSpacing(15)
        buttons_layout.setContentsMargins(20, 10, 20, 10)

        edit_btn = QPushButton("✏️")
        edit_btn.setObjectName("edit_btn")
        edit_btn.setToolTip("Редактировать рецепт")
        edit_btn.setFixedSize(70, 70)
        edit_btn.clicked.connect(self.edit_recipe)

        add_to_cart_btn = QPushButton("🛒")
        add_to_cart_btn.setObjectName("cart_btn")
        add_to_cart_btn.setToolTip("Добавить ингредиенты в корзину")
        add_to_cart_btn.setFixedSize(70, 70)
        add_to_cart_btn.clicked.connect(self.on_add_to_cart)

        delete_btn = QPushButton("🗑️")
        delete_btn.setObjectName("delete_btn")
        delete_btn.setToolTip("Удалить рецепт")
        delete_btn.setFixedSize(70, 70)
        delete_btn.clicked.connect(self.delete_recipe)

        is_favorite = self.db.is_favorite(self.user_id, self.recipe.id)
        favorite_icon = "❤️" if is_favorite else "🤍"
        self.favorite_btn = QPushButton(favorite_icon)
        self.favorite_btn.setObjectName("favorite_btn")
        self.favorite_btn.setToolTip("Убрать из избранного" if is_favorite else "Добавить в избранное")
        self.favorite_btn.setFixedSize(70, 70)
        self.favorite_btn.clicked.connect(self.toggle_favorite)

        is_cooked = self.db.is_cooked(self.user_id, self.recipe.id)
        cooked_icon = "✅" if is_cooked else "⏳"
        self.cooked_btn = QPushButton(cooked_icon)
        self.cooked_btn.setObjectName("cooked_btn")
        self.cooked_btn.setToolTip("Снять отметку приготовления" if is_cooked else "Отметить как приготовленное")
        self.cooked_btn.setFixedSize(70, 70)
        self.cooked_btn.clicked.connect(self.toggle_cooked_status)

        buttons_layout.addStretch()
        buttons_layout.addWidget(edit_btn)
        buttons_layout.addWidget(add_to_cart_btn)
        buttons_layout.addWidget(delete_btn)
        buttons_layout.addWidget(self.favorite_btn)
        buttons_layout.addWidget(self.cooked_btn)
        buttons_layout.addStretch()

        layout.addWidget(buttons_container)
        layout.addStretch()

        scroll.setWidget(content_widget)

        # Основной layout диалога
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

    def edit_recipe(self):
        """Открывает диалог редактирования рецепта"""
        try:
            dialog = RecipeDialog(self.db, self.user_id, self.recipe.id)
            dialog.recipe_saved.connect(self.recipe_updated)
            dialog.exec()
            self.close()
        except Exception as e:
            print(f"Ошибка при открытии редактора рецепта: {e}")

    def delete_recipe(self):
        """Удаляет рецепт после подтверждения"""
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            "Вы действительно хотите удалить этот рецепт?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.db.delete_recipe(self.recipe.id)
                if success:
                    self.recipe_deleted.emit(self.recipe.id)
                    self.close()
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось удалить рецепт")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка при удалении рецепта: {e}")

    def format_instructions(self, instructions):
        """Форматирует инструкции с автоматической нумерацией и улучшенным видом"""
        if not instructions:
            return "Инструкции отсутствуют"

        steps = instructions.split('\n')
        numbered_steps = []

        for i, step in enumerate(steps, 1):
            step = step.strip()
            if step:
                # Убираем существующую нумерацию если есть
                if step and step[0].isdigit() and '.' in step.split()[0]:
                    step = step.split('.', 1)[1].strip()
                numbered_steps.append(f"{i}. {step}")

        if not numbered_steps:
            return "Инструкции отсутствуют"

        return '\n\n'.join(numbered_steps)

    def on_add_to_cart(self):
        """Добавляет ингредиенты рецепта в корзину"""
        try:
            ingredients = self.db.get_recipe_ingredients(self.recipe.id)
            self.add_to_cart.emit(ingredients)  # ingredients - список кортежей
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", "Не удалось добавить ингредиенты в корзину")

    def toggle_favorite(self):
        """Добавляет или убирает рецепт из избранного"""
        try:
            is_favorite = self.db.is_recipe_favorite(self.user_id, self.recipe.id)

            if is_favorite:
                success = self.db.toggle_favorite(self.user_id, self.recipe.id)
                new_status = False
            else:
                success = self.db.toggle_favorite(self.user_id, self.recipe.id)
                new_status = True

            if success:
                favorite_icon = "❤️" if new_status else "🤍"
                tooltip = "Убрать из избранного" if new_status else "Добавить в избранное"

                self.favorite_btn.setText(favorite_icon)
                self.favorite_btn.setToolTip(tooltip)
                self.recipe_updated.emit()

                action = "добавлен в" if new_status else "удален из"
                QMessageBox.information(self, "Избранное",
                                        f"Рецепт '{self.recipe.name}' {action} избранное!")
        except Exception:
            QMessageBox.critical(self, "Ошибка", "Не удалось изменить статус избранного")

    def toggle_cooked_status(self):
        """Переключает статус приготовления рецепта"""
        try:
            is_cooked = self.db.is_recipe_cooked(self.user_id, self.recipe.id)
            success = self.db.mark_recipe_as_cooked(self.user_id, self.recipe.id, not is_cooked)

            if success:
                new_status = not is_cooked
                cooked_icon = "✅" if new_status else "⏳"
                tooltip = "Снять отметку приготовления" if new_status else "Отметить как приготовленное"

                self.cooked_btn.setText(cooked_icon)
                self.cooked_btn.setToolTip(tooltip)
                self.recipe_updated.emit()

                action = "отмечен как приготовленный" if new_status else "снята отметка приготовления"
                QMessageBox.information(self, "Приготовлено",
                                        f"Рецепт '{self.recipe.name}' {action}!")
        except Exception:
            QMessageBox.critical(self, "Ошибка", "Не удалось изменить статус приготовления")

