from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QListWidget, QListWidgetItem, QMessageBox,
                             QFileDialog, QCheckBox, QDialog, QLineEdit,
                             QComboBox, QDoubleSpinBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor


class CartItemWidget(QWidget):
    """Виджет для отображения элемента корзины с чекбоксом"""

    def __init__(self, ingredient_name, quantity, unit, parent=None):
        super().__init__(parent)
        self.ingredient_name = ingredient_name
        self.quantity = quantity
        self.unit = unit
        self.init_ui()

    def init_ui(self):
        """Инициализация пользовательского интерфейса виджета"""
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)

        self.checkbox = QCheckBox()
        self.checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """)

        # Форматируем количество
        quantity_text = str(self.quantity)
        try:
            quantity_float = float(self.quantity)
            if quantity_float == int(quantity_float):
                quantity_text = str(int(quantity_float))
            else:
                quantity_text = f"{quantity_float:.2f}"
        except ValueError:
            pass

        text_label = QLabel(f"{self.ingredient_name}: {quantity_text} {self.unit}")
        text_label.setStyleSheet("""
            QLabel { 
                color: #2c3e50;
                font-size: 14px;
                padding: 5px;
            }
        """)

        layout.addWidget(self.checkbox)
        layout.addWidget(text_label)
        layout.addStretch()

        self.setLayout(layout)

    def is_checked(self):
        """Проверяет, отмечен ли чекбокс"""
        return self.checkbox.isChecked()


class AddIngredientDialog(QDialog):
    """Диалог для добавления пользовательских ингредиентов в корзину"""

    def __init__(self, db, parent=None):
        """Инициализация диалога добавления ингредиента"""
        super().__init__(parent)
        self.db = db
        self.ingredient_data = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Добавить ингредиент")
        self.setFixedSize(400, 200)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # ПОЛЕ ВВОДА НАЗВАНИЯ ИНГРЕДИЕНТА
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Ингредиент:"))

        # Выпадающий список существующих ингредиентов
        self.name_combo = QComboBox()
        ingredients = self.db.get_ingredients()
        for ing_id, ing_name in ingredients:
            self.name_combo.addItem(ing_name)

        # Поле для ввода нового ингредиента
        self.custom_name_input = QLineEdit()
        self.custom_name_input.setPlaceholderText("Или введите новый ингредиент...")

        name_layout.addWidget(self.name_combo)
        name_layout.addWidget(self.custom_name_input)
        layout.addLayout(name_layout)

        # ПОЛЯ ДЛЯ ВВОДА КОЛИЧЕСТВА И ЕДИНИЦЫ ИЗМЕРЕНИЯ
        quantity_layout = QHBoxLayout()
        quantity_layout.addWidget(QLabel("Количество:"))

        # Спинбокс для ввода количества
        self.quantity_input = QDoubleSpinBox()
        self.quantity_input.setRange(0.1, 10000)
        self.quantity_input.setDecimals(2)
        self.quantity_input.setValue(100)

        # Выпадающий список единиц измерения
        self.unit_combo = QComboBox()
        units = ["г", "кг", "мл", "л", "шт", "ст.л.", "ч.л.", "стакан", "щепотка", "по вкусу"]
        self.unit_combo.addItems(units)

        quantity_layout.addWidget(self.quantity_input)
        quantity_layout.addWidget(self.unit_combo)
        quantity_layout.addStretch()
        layout.addLayout(quantity_layout)

        # ПАНЕЛЬ КНОПОК УПРАВЛЕНИЯ
        buttons_layout = QHBoxLayout()

        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.add_ingredient)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)

        buttons_layout.addWidget(add_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def add_ingredient(self):
        """Добавление ингредиента в корзину с валидацией данных"""
        # ПОЛУЧЕНИЕ НАЗВАНИЯ ИНГРЕДИЕНТА
        name = self.custom_name_input.text().strip()
        if not name:
            name = self.name_combo.currentText()

        # ПРОВЕРКА НАЛИЧИЯ НАЗВАНИЯ
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название ингредиента")
            return

        # ПОЛУЧЕНИЕ КОЛИЧЕСТВА И ЕДИНИЦЫ ИЗМЕРЕНИЯ
        quantity = self.quantity_input.value()
        unit = self.unit_combo.currentText()

        # СОХРАНЕНИЕ ДАННЫХ ИНГРЕДИЕНТА
        self.ingredient_data = {
            'name': name,
            'quantity': quantity,
            'unit': unit
        }

        # Если это новый ингредиент, добавляем его в базу
        if name == self.custom_name_input.text().strip():
            self.db.add_ingredient(name)

        self.accept()

    def get_ingredient_data(self):
        """Возвращает данные ингредиента"""
        return self.ingredient_data


class CartWidget(QWidget):
    """Виджет корзины покупок"""

    add_to_cart_signal = pyqtSignal(list)

    def __init__(self, db, user_id, main_window):
        super().__init__()
        self.db = db
        self.user_id = user_id
        self.main_window = main_window
        self.cart = []

        self.init_ui()
        self.update_cart()

    def init_ui(self):
        """Инициализация пользовательского интерфейса корзины"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Заголовок
        cart_header = QLabel("🛒 Корзина ингредиентов")
        cart_header.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
        """)
        layout.addWidget(cart_header)

        # Кнопки управления корзиной
        cart_buttons_layout = QHBoxLayout()

        add_ingredient_btn = QPushButton("➕ Добавить ингредиент")
        add_ingredient_btn.clicked.connect(self.show_add_ingredient_dialog)

        clear_cart_btn = QPushButton("🗑️ Очистить корзину")
        clear_cart_btn.clicked.connect(self.clear_cart)

        remove_selected_btn = QPushButton("❌ Удалить выбранные")
        remove_selected_btn.clicked.connect(self.remove_selected_items)

        export_cart_btn = QPushButton("📄 Экспорт списка")
        export_cart_btn.clicked.connect(self.export_cart)

        cart_buttons_layout.addWidget(add_ingredient_btn)
        cart_buttons_layout.addWidget(clear_cart_btn)
        cart_buttons_layout.addWidget(remove_selected_btn)
        cart_buttons_layout.addWidget(export_cart_btn)
        cart_buttons_layout.addStretch()

        layout.addLayout(cart_buttons_layout)

        # Список ингредиентов
        self.cart_list = QListWidget()
        self.cart_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.cart_list.setStyleSheet("""
            QListWidget {
                font-size: 14px;
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 0px;
                border-bottom: 1px solid #f1f3f4;
            }
            QListWidget::item:last {
                border-bottom: none;
            }
        """)
        layout.addWidget(self.cart_list, 1)

        self.setLayout(layout)

    def update_cart(self):
        """Обновляет корзину из базы данных"""
        try:
            self.cart = self.db.get_cart_items(self.user_id)
            self.update_display()
        except Exception as e:
            print(f"Ошибка обновления корзины: {e}")

    def update_display(self):
        """Обновляет отображение корзины"""
        self.cart_list.clear()

        if not self.cart:
            empty_item = QListWidgetItem("🛒 Корзина пуста")
            empty_item.setFlags(empty_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            empty_item.setForeground(QColor(108, 117, 125))
            self.cart_list.addItem(empty_item)
            return

        # Группируем ингредиенты
        ingredient_groups = {}
        for item in self.cart:
            name = item['name']
            quantity = item['quantity']
            unit = item['unit']
            key = (name, unit)

            if key in ingredient_groups:
                try:
                    existing_qty = float(ingredient_groups[key]) if str(ingredient_groups[key]).replace('.',
                                                                                                        '').isdigit() else 0
                    new_qty = float(quantity) if str(quantity).replace('.', '').isdigit() else 0
                    ingredient_groups[key] = existing_qty + new_qty
                except:
                    pass
            else:
                ingredient_groups[key] = quantity

        # Создаем виджеты для каждого ингредиента
        for (name, unit), total_quantity in ingredient_groups.items():
            item_widget = CartItemWidget(name, total_quantity, unit)
            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())
            list_item.setBackground(QColor(248, 249, 250))
            self.cart_list.addItem(list_item)
            self.cart_list.setItemWidget(list_item, item_widget)

    def show_add_ingredient_dialog(self):
        """Показывает диалог добавления ингредиента"""
        dialog = AddIngredientDialog(self.db, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            ingredient_data = dialog.get_ingredient_data()
            if ingredient_data:
                self.cart.append({
                    'name': ingredient_data['name'],
                    'quantity': ingredient_data['quantity'],
                    'unit': ingredient_data['unit']
                })
                self.add_to_cart([(
                    ingredient_data['name'],
                    ingredient_data['quantity'],
                    ingredient_data['unit']
                )])

    def add_to_cart(self, ingredients):
        """Добавляет ингредиенты в корзину"""
        try:
            success_count = 0
            for name, quantity, unit in ingredients:
                success = self.db.add_cart_item(
                    self.user_id, name, quantity, unit
                )
                if success:
                    success_count += 1

            if success_count > 0:
                self.update_cart()
                if self.main_window and hasattr(self.main_window, 'update_profile'):
                    self.main_window.update_profile()
                QMessageBox.information(self, "Успех", f"Добавлено {success_count} ингредиентов в корзину!")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось добавить ингредиенты в корзину")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", "Не удалось добавить в корзину")

    def remove_selected_items(self):
        """Удаляет выбранные элементы из корзины"""
        try:
            items_to_remove = []
            for i in range(self.cart_list.count()):
                item = self.cart_list.item(i)
                widget = self.cart_list.itemWidget(item)
                if widget and widget.is_checked():
                    items_to_remove.append({
                        'name': widget.ingredient_name,
                        'unit': widget.unit
                    })

            if items_to_remove:
                success = self.db.remove_cart_items(self.user_id, items_to_remove)
                if success:
                    self.update_cart()
                    if self.main_window and hasattr(self.main_window, 'update_profile'):
                        self.main_window.update_profile()
                    QMessageBox.information(self, "Успех", f"Удалено {len(items_to_remove)} ингредиентов")
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось удалить элементы из корзины")
            else:
                QMessageBox.information(self, "Информация", "Не выбраны ингредиенты для удаления")

        except Exception as e:
            print(f"Ошибка удаления из корзины: {e}")
            QMessageBox.critical(self, "Ошибка", "Не удалось удалить элементы")

    def clear_cart(self):
        """Очищает всю корзину"""
        try:
            if not self.cart:
                QMessageBox.information(self, "Информация", "Корзина уже пуста")
                return

            reply = QMessageBox.question(
                self,
                "Подтверждение",
                "Вы действительно хотите очистить корзину?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                success = self.db.clear_cart(self.user_id)
                if success:
                    self.cart = []
                    self.update_display()
                    if self.main_window and hasattr(self.main_window, 'update_profile'):
                        self.main_window.update_profile()
                    QMessageBox.information(self, "Успех", "Корзина очищена!")
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось очистить корзину")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", "Не удалось очистить корзину")

    def export_cart(self):
        """Экспортирует список покупок в текстовый файл"""
        if not self.cart:
            QMessageBox.warning(self, "Ошибка", "Корзина пуста!")
            return

        try:
            file_name, _ = QFileDialog.getSaveFileName(
                self, "Сохранить список покупок", "список_покупок.txt", "Text files (*.txt)"
            )

            if file_name:
                with open(file_name, 'w', encoding='utf-8') as f:
                    f.write("Список покупок:\n")
                    f.write("=" * 50 + "\n\n")

                    ingredient_groups = {}
                    for item in self.cart:
                        name = item['name']
                        quantity = item['quantity']
                        unit = item['unit']
                        key = (name, unit)
                        if key in ingredient_groups:
                            try:
                                ingredient_groups[key] += float(quantity)
                            except:
                                ingredient_groups[key] = quantity
                        else:
                            try:
                                ingredient_groups[key] = float(quantity)
                            except:
                                ingredient_groups[key] = quantity

                    for (name, unit), total_quantity in ingredient_groups.items():
                        if isinstance(total_quantity, float):
                            f.write(f"• {name}: {total_quantity:.1f} {unit}\n")
                        else:
                            f.write(f"• {name}: {total_quantity} {unit}\n")

                QMessageBox.information(self, "Успех", f"Список сохранен в файл: {file_name}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать список: {e}")