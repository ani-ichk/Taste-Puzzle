import re
import shutil
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, ForeignKey, Table, text, DateTime, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import inspect
from datetime import datetime
import os

# Базовый класс для моделей SQLAlchemy
Base = declarative_base()

# Ассоциативные таблицы для связей многие-ко-многим
recipe_ingredients = Table(
    'Recipe_ingredients', Base.metadata,
    Column('recipe_id', Integer, ForeignKey('Recipes.id'), primary_key=True),
    Column('ingredient_id', Integer, ForeignKey('Ingredients.id'), primary_key=True),
    Column('quantity', Float, nullable=False)
)

favorites = Table(
    'Favorites', Base.metadata,
    Column('user_id', Integer, ForeignKey('Users.id'), primary_key=True),
    Column('recipe_id', Integer, ForeignKey('Recipes.id'), primary_key=True)
)


# МОДЕЛЬ КОРЗИНЫ
class Cart(Base):
    __tablename__ = 'cart'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('Users.id'), nullable=False)
    ingredient_name = Column(String(200), nullable=False)
    quantity = Column(String(50), nullable=False)
    unit = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="cart_items")


# МОДЕЛЬ ДЛЯ ОТМЕТКИ ПРИГОТОВЛЕННЫХ РЕЦЕПТОВ
class CookedRecipe(Base):
    __tablename__ = 'cooked_recipes'

    user_id = Column(Integer, ForeignKey('Users.id'), primary_key=True)
    recipe_id = Column(Integer, ForeignKey('Recipes.id'), primary_key=True)
    cooked_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="cooked_recipes")
    recipe = relationship("Recipe", back_populates="cooked_by_users")


# МОДЕЛЬ ПОЛЬЗОВАТЕЛЯ
class User(Base):
    __tablename__ = 'Users'

    id = Column(Integer, primary_key=True)
    login = Column(String(50), nullable=False)
    password = Column(String(100), nullable=False)

    cart_items = relationship("Cart", back_populates="user")
    recipes = relationship("Recipe", back_populates="user")
    favorite_recipes = relationship("Recipe", secondary=favorites, back_populates="favorited_by")
    cooked_recipes = relationship("CookedRecipe", back_populates="user")


# МОДЕЛЬ ТИПА БЛЮДА (категории)
class Dish_types(Base):
    __tablename__ = 'Dish_types'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)

    recipes = relationship("Recipe", back_populates="dish_type")


# МОДЕЛЬ КУХНИ
class Cuisines(Base):
    __tablename__ = 'Cuisines'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)

    recipes = relationship("Recipe", back_populates="cuisine")


# МОДЕЛЬ РЕЦЕПТА
class Recipe(Base):
    __tablename__ = 'Recipes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('Users.id'), nullable=False)
    name = Column(String(200), nullable=False)
    instruction = Column(Text)
    description = Column(Text)
    dish_type_id = Column(Integer, ForeignKey('Dish_types.id'), nullable=True)
    cuisine_id = Column(Integer, ForeignKey('Cuisines.id'), nullable=True)
    cook_time = Column(Integer)
    external_url = Column(String(500))
    image = Column(String(500))
    servings = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)

    # Связи
    user = relationship("User", back_populates="recipes")
    dish_type = relationship("Dish_types", back_populates="recipes")
    cuisine = relationship("Cuisines", back_populates="recipes")
    ingredients = relationship("Ingredient", secondary=recipe_ingredients, back_populates="recipes")
    favorited_by = relationship("User", secondary=favorites, back_populates="favorite_recipes")
    nutrition = relationship("Nutrition", back_populates="recipe", uselist=False)
    cooked_by_users = relationship("CookedRecipe", back_populates="recipe")


# МОДЕЛЬ КАТЕГОРИИ РЕЦЕПТОВ
class Category(Base):
    __tablename__ = 'Categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50))

# МОДЕЛЬ ИНГРЕДИЕНТА
class Ingredient(Base):
    __tablename__ = 'Ingredients'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)

    recipes = relationship("Recipe", secondary=recipe_ingredients, back_populates="ingredients")


# МОДЕЛЬ ПИЩЕВОЙ ЦЕННОСТИ
class Nutrition(Base):
    __tablename__ = 'Nutrition'

    recipe_id = Column(Integer, ForeignKey('Recipes.id'), primary_key=True)
    calories = Column(Integer)
    proteins = Column(Float)
    fats = Column(Float)
    carbohydrates = Column(Float)

    recipe = relationship("Recipe", back_populates="nutrition")


class DataBase:
    def __init__(self):
        """Инициализация подключения к базе данных"""
        try:
            db_path = os.path.join('../data/Taste_Pazzle.db')

            self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
            self.Session = sessionmaker(bind=self.engine)

            Base.metadata.create_all(self.engine)

            # Создаем дополнительные таблицы если их нет
            self._create_additional_tables()

            # Добавляем отсутствующие столбцы
            self._migrate_database()

            self._check_existing_data()

            self._check_existing_data()

            self.assign_unique_images_to_recipes()
            self.check_image_status()
            self.migrate_existing_images()


        except Exception as e:
            print(f"Ошибка подключения к базе данных: {e}")
            raise

    def _migrate_database(self):
        """Упрощенная миграция - просто создаем все таблицы"""
        try:
            # Создаем все таблицы из моделей
            Base.metadata.create_all(self.engine)

            session = self.Session()
            try:
                dish_type_names = ["Салаты", "Десерты", "Основные блюда", "Завтраки", "Гарниры", "Супы"]
                for name in dish_type_names:
                    existing = session.query(Dish_types).filter_by(name=name).first()
                    if not existing:
                        dish_type = Dish_types(name=name)
                        session.add(dish_type)

                session.commit()
            finally:
                session.close()

        except Exception as e:
            raise

    def migrate_existing_images(self):
        """Мигрирует существующие пути изображений к новому формату"""
        session = self.Session()
        try:
            recipes = session.query(Recipe).filter(Recipe.image.isnot(None)).all()
            migrated_count = 0

            for recipe in recipes:
                if recipe.image and isinstance(recipe.image, str):
                    if '/' in recipe.image or '\\' in recipe.image:
                        old_path = recipe.image
                        new_filename = os.path.basename(old_path)
                        recipe.image = new_filename
                        migrated_count += 1

            if migrated_count > 0:
                session.commit()

        except Exception as e:
            session.rollback()
        finally:
            session.close()

    def assign_unique_images_to_recipes(self):
        """Назначает каждому рецепту уникальное изображение на основе его названия"""
        session = self.Session()
        try:
            available_images = [
                'apple_pie.jpg', 'cabbage_rolls.jpg', 'caesar.jpg',
                'mashed_potatoes.jpg', 'olivier.jpg', 'ramen.jpg',
                'french_toast.jpg', 'pasta_carbonara.jpg'
            ]

            keyword_mapping = {
                'яблочн': 'apple_pie.jpg',
                'пирог': 'apple_pie.jpg',
                'голубц': 'cabbage_rolls.jpg',
                'капуст': 'cabbage_rolls.jpg',
                'цезар': 'caesar.jpg',
                'салат цезар': 'caesar.jpg',
                'картофельн': 'mashed_potatoes.jpg',
                'пюре': 'mashed_potatoes.jpg',
                'картошк': 'mashed_potatoes.jpg',
                'оливье': 'olivier.jpg',
                'салат оливье': 'olivier.jpg',
                'рамен': 'ramen.jpg',
                'лапш': 'ramen.jpg',
                'французск': 'french_toast.jpg',
                'френч': 'french_toast.jpg',
                'тост': 'french_toast.jpg',
                'карбонар': 'pasta_carbonara.jpg',
                'паста': 'pasta_carbonara.jpg',
                'спагетт': 'pasta_carbonara.jpg',
                'макарон': 'pasta_carbonara.jpg'
            }

            recipes = session.query(Recipe).all()

            used_images = set()
            updated_count = 0

            for recipe in recipes:
                # Пропускаем рецепты, у которых уже есть изображение
                if recipe.image and recipe.image.strip():
                    used_images.add(recipe.image)
                    continue

                recipe_name_lower = recipe.name.lower()
                image_assigned = False

                # Сначала проверяем по ключевым словам
                for keyword, image_file in keyword_mapping.items():
                    if keyword in recipe_name_lower:
                        # Создаем уникальное имя для изображения
                        import hashlib
                        recipe_hash = hashlib.md5(f"{recipe.id}_{recipe.name}".encode()).hexdigest()[:8]
                        unique_image_name = f"{recipe_hash}_{image_file}"

                        # Копируем изображение с уникальным именем
                        current_dir = os.path.dirname(os.path.abspath(__file__))
                        project_root = os.path.dirname(current_dir)
                        images_dir = os.path.join(project_root, 'img', 'recipe_img')

                        original_path = os.path.join(images_dir, image_file)
                        unique_path = os.path.join(images_dir, unique_image_name)

                        if os.path.exists(original_path):
                            try:
                                import shutil
                                shutil.copy2(original_path, unique_path)
                                recipe.image = unique_image_name
                                used_images.add(unique_image_name)
                                updated_count += 1
                                image_assigned = True
                                break
                            except Exception as e:
                                continue

                # Если не назначили по ключевому слову, используем хэш
                if not image_assigned and available_images:
                    import hashlib
                    recipe_hash = hashlib.md5(f"{recipe.id}_{recipe.name}".encode()).hexdigest()[:8]
                    hash_int = int(hashlib.md5(recipe.name.encode()).hexdigest()[:8], 16)
                    image_index = hash_int % len(available_images)

                    for i in range(len(available_images)):
                        current_index = (image_index + i) % len(available_images)
                        image_file = available_images[current_index]

                        # Создаем уникальное имя
                        unique_image_name = f"{recipe_hash}_{image_file}"

                        if unique_image_name not in used_images:
                            # Копируем изображение
                            current_dir = os.path.dirname(os.path.abspath(__file__))
                            project_root = os.path.dirname(current_dir)
                            images_dir = os.path.join(project_root, 'img', 'recipe_img')

                            original_path = os.path.join(images_dir, image_file)
                            unique_path = os.path.join(images_dir, unique_image_name)

                            if os.path.exists(original_path):
                                try:
                                    import shutil
                                    shutil.copy2(original_path, unique_path)
                                    recipe.image = unique_image_name
                                    used_images.add(unique_image_name)
                                    updated_count += 1
                                    image_assigned = True
                                    break
                                except Exception as e:
                                    continue

                if not image_assigned and available_images:
                    # Если всё ещё не назначили, создаем последний вариант
                    import hashlib
                    recipe_hash = hashlib.md5(f"{recipe.id}_{recipe.name}".encode()).hexdigest()[:8]
                    unique_image_name = f"{recipe_hash}_{available_images[0]}"

                    # Копируем изображение
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    project_root = os.path.dirname(current_dir)
                    images_dir = os.path.join(project_root, 'img', 'recipe_img')

                    original_path = os.path.join(images_dir, available_images[0])
                    unique_path = os.path.join(images_dir, unique_image_name)

                    if os.path.exists(original_path):
                        try:
                            import shutil
                            shutil.copy2(original_path, unique_path)
                            recipe.image = unique_image_name
                            updated_count += 1
                        except Exception as e:
                            pass

            session.commit()
            self._verify_image_assignments()

        except Exception as e:
            session.rollback()
            import traceback
            print(traceback.format_exc())
        finally:
            session.close()

    def _verify_image_assignments(self):
        """Проверяет, что все рецепты имеют уникальные изображения"""
        session = self.Session()
        try:
            recipes = session.query(Recipe).all()
            image_count = {}

            for recipe in recipes:
                if recipe.image:
                    if recipe.image in image_count:
                        image_count[recipe.image] += 1
                    else:
                        image_count[recipe.image] = 1

            for image_file, count in image_count.items():
                status = "OK" if count == 1 else "ПОВТОР"
                print(f"{image_file}: {count} рецептов - {status}")

            recipes_without_images = [r for r in recipes if not r.image]
            if recipes_without_images:
                print(f"Рецепты без изображений: {len(recipes_without_images)}")
                for recipe in recipes_without_images:
                    print(f"  - {recipe.name}")

        except Exception as e:
            print(f"Ошибка при проверке назначения изображений: {e}")
        finally:
            session.close()

    def check_image_status(self):
        """Проверяет статус изображений в базе данных"""
        session = self.Session()
        try:
            total_recipes = session.query(Recipe).count()
            recipes_with_images = session.query(Recipe).filter(Recipe.image.isnot(None)).all()

            available_images = 0
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            images_dir = os.path.join(project_root, 'img', 'recipe_img')

            for recipe in recipes_with_images:
                if recipe.image and isinstance(recipe.image, str):
                    image_path = os.path.join(images_dir, recipe.image)
                    if os.path.exists(image_path):
                        available_images += 1

            recipes = session.query(Recipe).all()
            for recipe in recipes:
                if recipe.image:
                    image_path = os.path.join(images_dir, recipe.image)
                    status = "Есть файл" if os.path.exists(image_path) else "Файл не найден"
                else:
                    status = "Нет изображения"

        except Exception as e:
            print(f"Ошибка проверки статуса изображений: {e}")
        finally:
            session.close()

    def _create_additional_tables(self):
        """Создает дополнительные таблицы если они не существуют"""
        try:
            inspector = inspect(self.engine)
            existing_tables = inspector.get_table_names()

            if 'cart' not in existing_tables:
                Cart.__table__.create(self.engine, checkfirst=True)

            if 'cooked_recipes' not in existing_tables:
                CookedRecipe.__table__.create(self.engine, checkfirst=True)

        except Exception as e:
            print(f"Ошибка создания дополнительных таблиц: {e}")
            raise

    def _check_existing_data(self):
        """Проверяет и выводит информацию о существующих данных в БД"""
        session = self.Session()
        try:
            # Проверяем наличие столбца created_at
            inspector = inspect(self.engine)
            columns = [col['name'] for col in inspector.get_columns('Recipes')]

            if 'created_at' in columns:
                recipes_count = session.query(Recipe).count()
            else:
                # Если столбца нет, используем альтернативный запрос
                recipes_count = session.execute(text("SELECT COUNT(*) FROM Recipes")).scalar()

            users_count = session.query(User).count()
            categories_count = session.query(Category).count()
            ingredients_count = session.query(Ingredient).count()

            # Выводим первых 5 пользователей для отладки
            users = session.query(User).limit(5).all()

        except Exception as e:
            print(f"Ошибка при проверке данных БД: {e}")
        finally:
            session.close()


    # ===== МЕТОДЫ ДЛЯ РАБОТЫ С КАТЕГОРИЯМИ =====
    def get_dish_types(self):
        """Получает список типов блюд"""
        session = self.Session()
        try:
            dish_types = session.query(Dish_types).all()
            return [(dt.id, dt.name) for dt in dish_types]
        finally:
            session.close()

    def get_cuisines(self):
        """Получает список кухонь"""
        session = self.Session()
        try:
            cuisines = session.query(Cuisines).all()
            return [(c.id, c.name) for c in cuisines]
        finally:
            session.close()

    def get_dish_type_by_name(self, dish_type_name):
        """Получает ID типа блюда по названию"""
        session = self.Session()
        try:
            dish_type = session.query(Dish_types).filter(Dish_types.name == dish_type_name).first()
            return dish_type.id if dish_type else None
        finally:
            session.close()

    def get_cuisine_by_name(self, cuisine_name):
        """Получает ID кухни по названию"""
        session = self.Session()
        try:
            cuisine = session.query(Cuisines).filter(Cuisines.name == cuisine_name).first()
            return cuisine.id if cuisine else None
        finally:
            session.close()

    def get_categories(self):
        """Получение всех категорий"""
        session = self.Session()
        try:
            categories = session.query(Category).all()
            return [(cat.id, cat.name, cat.type) for cat in categories]
        except Exception as e:
            return []
        finally:
            session.close()

    # Для обратной совместимости
    def get_categories_by_type(self, category_type):
        """Получает категории по типу (cuisine или dish_type)"""
        if category_type == 'dish_type':
            return self.get_dish_types()  # Без аргументов
        elif category_type == 'cuisine':
            return self.get_cuisines()  # Без аргументов
        else:
            # Для старых категорий из таблицы Categories
            session = self.Session()
            try:
                categories = session.query(Category).filter(Category.type == category_type).all()
                return [(cat.id, cat.name) for cat in categories]
            finally:
                session.close()

    # ===== МЕТОДЫ ДЛЯ РАБОТЫ С РЕЦЕПТАМИ =====

    def get_recipe_image(self, recipe_id):
        """Упрощенная загрузка изображения рецепта"""
        try:
            session = self.Session()
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()

            if recipe and recipe.image:
                image_path = f"../img/recipe_img/{recipe.image}"
                from PyQt6.QtGui import QPixmap
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    session.close()
                    return pixmap

            recipe_name = recipe.name if recipe else "Рецепт"
            session.close()
            return self._create_text_pixmap(recipe_name)

        except Exception as e:
            return self._create_text_pixmap("Изображение")

    def _create_text_pixmap(self, text):
        """Создает QPixmap с текстовой заглушкой"""
        from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
        from PyQt6.QtCore import Qt

        pixmap = QPixmap(200, 150)
        pixmap.fill(QColor(240, 240, 240))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)

        painter.setPen(QColor(100, 100, 100))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()

        return pixmap

    def _parse_quantity(self, quantity_str):
        """Парсит количество из строки в числовое значение и определяет единицу измерения"""
        try:
            if isinstance(quantity_str, (int, float)):
                return float(quantity_str), 'г'

            numbers = re.findall(r'\d+\.?\d*', str(quantity_str))
            if numbers:
                quantity = float(numbers[0])
                unit = 'г'
                quantity_lower = str(quantity_str).lower()

                if 'шт' in quantity_lower or 'штук' in quantity_lower:
                    unit = 'шт'
                elif 'ст' in quantity_lower or 'стакан' in quantity_lower:
                    unit = 'стакан'
                elif 'ст.л.' in quantity_lower or 'стол' in quantity_lower:
                    unit = 'ст.л.'
                elif 'ч.л.' in quantity_lower or 'чай' in quantity_lower:
                    unit = 'ч.л.'
                elif 'мл' in quantity_lower:
                    unit = 'мл'
                elif 'л' in quantity_lower and 'мл' not in quantity_lower:
                    unit = 'л'
                elif 'кг' in quantity_lower:
                    unit = 'кг'
                elif 'г' in quantity_lower and 'кг' not in quantity_lower:
                    unit = 'г'

                return quantity, unit
            else:
                return 1.0, str(quantity_str)

        except Exception as e:
            return 1.0, 'шт'

    def save_recipe_image(self, image_data, recipe_id, recipe_name):
        """Сохраняет изображение рецепта с уникальным именем и возвращает имя файла"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            images_dir = os.path.join(project_root, 'img', 'recipe_img')
            os.makedirs(images_dir, exist_ok=True)

            # Создаем уникальное имя файла на основе ID рецепта
            import hashlib
            recipe_hash = hashlib.md5(f"{recipe_id}_{recipe_name}".encode()).hexdigest()[:8]

            # Определяем расширение файла
            if isinstance(image_data, str) and os.path.exists(image_data):
                extension = os.path.splitext(image_data)[1].lower()
            else:
                extension = '.jpg'

            image_filename = f"user_{recipe_hash}{extension}"
            image_path = os.path.join(images_dir, image_filename)

            if isinstance(image_data, bytes):
                with open(image_path, 'wb') as f:
                    f.write(image_data)
            elif isinstance(image_data, str) and os.path.exists(image_data):
                shutil.copy2(image_data, image_path)
            else:
                return None

            return image_filename

        except Exception as e:
            return None

    def add_recipe(self, user_id, name, instruction, description, dish_type_id, cuisine_id,
                   cook_time, ingredients_list, nutrition_data, image=None):
        """Добавление нового рецепта"""
        session = self.Session()
        try:

            # Проверяем существование dish_type_id и cuisine_id
            if dish_type_id:
                dish_type = session.query(Dish_types).get(dish_type_id)
                if not dish_type:
                    return None

            if cuisine_id:
                cuisine = session.query(Cuisines).get(cuisine_id)
                if not cuisine:
                    return None

            # Создаем рецепт
            new_recipe = Recipe(
                user_id=user_id,
                name=name,
                instruction=instruction,
                description=description,
                dish_type_id=dish_type_id,
                cuisine_id=cuisine_id,
                cook_time=cook_time
            )
            session.add(new_recipe)
            session.flush()

            # Обрабатываем изображение если оно есть
            image_filename = None
            if image:
                image_filename = self.save_recipe_image(image, new_recipe.id, name)
                new_recipe.image = image_filename
            else:
                # Если пользователь не загружено изображение, оставляем поле пустым
                new_recipe.image = None

            # Добавляем ингредиенты
            for ing_id, quantity, unit in ingredients_list:
                recipe_ingredient = recipe_ingredients.insert().values(
                    recipe_id=new_recipe.id,
                    ingredient_id=ing_id,
                    quantity=quantity
                )
                session.execute(recipe_ingredient)

            # Добавляем данные о питательности
            if any(nutrition_data):
                nutrition = Nutrition(
                    recipe_id=new_recipe.id,
                    calories=nutrition_data[0],
                    proteins=nutrition_data[1],
                    fats=nutrition_data[2],
                    carbohydrates=nutrition_data[3]
                )
                session.add(nutrition)

            session.commit()
            return new_recipe.id

        except Exception as e:
            session.rollback()
            return None
        finally:
            session.close()

    def get_recipe_by_id(self, recipe_id):
        """Получает рецепт по ID"""
        session = self.Session()
        try:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            return recipe
        except Exception:
            return None
        finally:
            session.close()

    def get_dish_types_with_objects(self):
        """Получает список типов блюд как объекты (для обратной совместимости)"""
        session = self.Session()
        try:
            dish_types = session.query(Dish_types).all()
            return dish_types
        except Exception:
            return []
        finally:
            session.close()

    def get_cuisines_with_objects(self):
        """Получает список кухонь как объекты (для обратной совместимости)"""
        session = self.Session()
        try:
            cuisines = session.query(Cuisines).all()
            return cuisines
        except Exception:
            return []
        finally:
            session.close()

    def add_to_favorites(self, user_id, recipe_id):
        """ Добавляет рецепт в избранное """
        return self.toggle_favorite(user_id, recipe_id)

    def remove_from_favorites(self, user_id, recipe_id):
        """ Удаляет рецепт из избранного """
        return self.toggle_favorite(user_id, recipe_id)

    def is_cooked(self, user_id, recipe_id):
        return self.is_recipe_cooked(user_id, recipe_id)

    def mark_as_cooked(self, user_id, recipe_id, cooked=True):
        """ Отмечает рецепт как приготовленный """
        return self.mark_recipe_as_cooked(user_id, recipe_id, cooked)

    def update_recipe(self, recipe_id, name, instruction, description, dish_type_id, cuisine_id,
                      cook_time, ingredients_list, nutrition_data, image=None):
        """Обновление существующего рецепта с раздельными полями для типа блюда и кухни"""
        session = self.Session()
        try:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                return False

            # Обновляем основные данные
            recipe.name = name
            recipe.instruction = instruction
            recipe.description = description
            recipe.dish_type_id = dish_type_id
            recipe.cuisine_id = cuisine_id
            recipe.cook_time = cook_time

            # Обрабатываем изображение если оно есть
            if image:
                image_filename = self.save_recipe_image(image, recipe_id, name)
                recipe.image = image_filename

            # Обновляем ингредиенты
            session.execute(
                recipe_ingredients.delete().where(recipe_ingredients.c.recipe_id == recipe_id)
            )
            for ing_id, quantity, unit in ingredients_list:
                session.execute(
                    recipe_ingredients.insert().values(
                        recipe_id=recipe_id,
                        ingredient_id=ing_id,
                        quantity=quantity
                    )
                )

            # Обновляем данные о питательности
            nutrition = session.query(Nutrition).filter_by(recipe_id=recipe_id).first()
            if nutrition:
                session.delete(nutrition)

            if any(nutrition_data):
                new_nutrition = Nutrition(
                    recipe_id=recipe_id,
                    calories=nutrition_data[0],
                    proteins=nutrition_data[1],
                    fats=nutrition_data[2],
                    carbohydrates=nutrition_data[3]
                )
                session.add(new_nutrition)

            session.commit()
            return True

        except Exception as e:
            session.rollback()
            return False
        finally:
            session.close()

    def get_recipes_with_filters(self, user_id, cuisine=None, max_time=None,
                                 favorites_only=False, cooked_only=False,
                                 ingredient_filter=None, name_filter=None):
        """Получение рецептов с фильтрами с группировкой по типам блюд"""
        session = self.Session()

        grouped_recipes = {}

        try:
            query = session.query(
                Recipe,
                Dish_types.name.label('dish_type_name'),
                Cuisines.name.label('cuisine_name')
            ).outerjoin(
                Dish_types, Recipe.dish_type_id == Dish_types.id
            ).outerjoin(
                Cuisines, Recipe.cuisine_id == Cuisines.id
            )

            # Фильтр по кухне
            if cuisine and cuisine != "Любая кухня":
                query = query.filter(Cuisines.name == cuisine)

            # Фильтр по времени приготовления
            if max_time:
                query = query.filter(Recipe.cook_time <= max_time)

            # Фильтр по избранному
            if favorites_only:
                favorite_subquery = session.query(favorites.c.recipe_id).filter(
                    favorites.c.user_id == user_id
                ).subquery()
                query = query.filter(Recipe.id.in_(favorite_subquery))

            # Фильтр по приготовленным рецептам
            if cooked_only:
                cooked_subquery = session.query(CookedRecipe.recipe_id).filter_by(user_id=user_id).subquery()
                query = query.filter(Recipe.id.in_(cooked_subquery))

            # Фильтр по названию
            if name_filter and name_filter.strip():
                name_filter = name_filter.strip()
                search_terms = [
                    f"%{name_filter}%",
                    f"%{name_filter.lower()}%",
                    f"%{name_filter.upper()}%",
                    f"%{name_filter.title()}%",
                ]
                search_terms = list(set(search_terms))
                conditions = []
                for term in search_terms:
                    conditions.append(Recipe.name.ilike(term))
                query = query.filter(or_(*conditions))

            # Фильтр по ингредиентам
            if ingredient_filter and isinstance(ingredient_filter, list) and ingredient_filter:

                # Для каждого ингредиента создаем под запрос
                subqueries = []
                for ing_name in ingredient_filter:
                    matching_ingredients = session.query(Ingredient).filter(
                        Ingredient.name.ilike(f'%{ing_name}%')
                    ).all()

                    if matching_ingredients:
                        ing_ids = [ing.id for ing in matching_ingredients]

                        # Создаем под запрос для текущего ингредиента
                        ing_subquery = session.query(recipe_ingredients.c.recipe_id).filter(
                            recipe_ingredients.c.ingredient_id.in_(ing_ids)
                        ).subquery()

                        # Добавляем в список под запросов
                        subqueries.append(ing_subquery)
                    else:
                        # Если один ингредиент не найден, возвращаем пустой результат
                        return {}

                # Объединяем все под запросы - рецепт должен содержать ВСЕ указанные ингредиенты
                if subqueries:
                    # Начинаем с первого под запроса
                    combined_subquery = subqueries[0]

                    # Пересекаем со всеми остальными под запросами
                    for subquery in subqueries[1:]:
                        combined_subquery = session.query(combined_subquery.c.recipe_id).intersect(
                            session.query(subquery.c.recipe_id)
                        ).subquery()

                    query = query.filter(Recipe.id.in_(combined_subquery))

            # Выполняем запрос
            results = query.all()

            for recipe, dish_type_name, cuisine_name in results:
                # Получаем данные о питательности
                nutrition = recipe.nutrition
                calories = nutrition.calories if nutrition else None
                proteins = nutrition.proteins if nutrition else None
                fats = nutrition.fats if nutrition else None
                carbohydrates = nutrition.carbohydrates if nutrition else None

                # Проверяем статусы
                is_favorite = session.query(favorites).filter_by(
                    user_id=user_id, recipe_id=recipe.id
                ).first() is not None

                is_cooked = session.query(CookedRecipe).filter_by(
                    user_id=user_id, recipe_id=recipe.id
                ).first() is not None

                dish_type = dish_type_name or "Основные блюда"

                recipe_tuple = (
                    recipe.id,
                    recipe.user_id,
                    recipe.name,
                    recipe.instruction,
                    recipe.description,
                    recipe.dish_type_id,
                    recipe.image,
                    recipe.external_url,
                    recipe.cook_time,
                    dish_type,
                    None,
                    calories,
                    proteins,
                    fats,
                    carbohydrates,
                    is_favorite,
                    is_cooked,
                    cuisine_name,
                    dish_type
                )

                # Динамически создаем категорию если её нет
                if dish_type not in grouped_recipes:
                    grouped_recipes[dish_type] = []

                grouped_recipes[dish_type].append(recipe_tuple)

            return grouped_recipes

        except Exception as e:
           return {}
        finally:
            session.close()

    def get_recipe_ingredients(self, recipe_id):
        """Получение ингредиентов рецепта"""
        session = self.Session()
        try:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if recipe:
                ingredients_data = []
                for ingredient in recipe.ingredients:
                    stmt = recipe_ingredients.select().where(
                        (recipe_ingredients.c.recipe_id == recipe_id) &
                        (recipe_ingredients.c.ingredient_id == ingredient.id)
                    )
                    result = session.execute(stmt).first()
                    if result:
                        quantity, unit = self._parse_quantity(result.quantity)
                        ingredients_data.append((ingredient.name, quantity, unit))
                return ingredients_data
            return []
        except Exception as e:
            return []
        finally:
            session.close()

    def delete_recipe(self, recipe_id):
        """Удаление рецепта"""
        session = self.Session()
        try:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if recipe:
                # Проверяем, используется ли это изображение другими рецептами
                can_delete_image = False
                if recipe.image and isinstance(recipe.image, str):
                    # Находим все рецепты с таким же именем файла изображения
                    same_image_recipes = session.query(Recipe).filter(
                        Recipe.image == recipe.image,
                        Recipe.id != recipe_id
                    ).count()

                    # Удаляем файл только если это уникальное изображение
                    if same_image_recipes == 0:
                        can_delete_image = True

                # Удаляем связанные записи
                session.execute(
                    recipe_ingredients.delete().where(recipe_ingredients.c.recipe_id == recipe_id)
                )
                session.execute(
                    favorites.delete().where(favorites.c.recipe_id == recipe_id)
                )

                nutrition = session.query(Nutrition).filter_by(recipe_id=recipe_id).first()
                if nutrition:
                    session.delete(nutrition)

                cooked_recipes = session.query(CookedRecipe).filter_by(recipe_id=recipe_id).all()
                for cooked_recipe in cooked_recipes:
                    session.delete(cooked_recipe)

                # Удаляем файл изображения если он существует и не используется другими рецептами
                if can_delete_image:
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    project_root = os.path.dirname(current_dir)
                    image_path = os.path.join(project_root, 'img', 'recipe_img', recipe.image)
                    if os.path.exists(image_path):
                        try:
                            os.remove(image_path)
                        except Exception as e:
                            print(f"Ошибка удаления файла изображения: {e}")
                    else:
                        print(f"Файл изображения не найден: {recipe.image}")
                else:
                    print(f"Изображение '{recipe.image}' используется другими рецептами, не удаляем")

                session.delete(recipe)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            return False
        finally:
            session.close()

    # ===== МЕТОДЫ ДЛЯ РАБОТЫ С КОРЗИНОЙ =====

    def get_cart_items(self, user_id):
        """Получает все элементы корзины для пользователя из БД"""
        session = self.Session()
        try:
            items = session.query(Cart).filter_by(user_id=user_id).all()
            return [{
                'name': item.ingredient_name,
                'quantity': item.quantity,
                'unit': item.unit
            } for item in items]
        except Exception as e:
            return []
        finally:
            session.close()

    def add_cart_item(self, user_id, ingredient_name, quantity, unit):
        """Добавляет элемент в корзину в БД"""
        session = self.Session()
        try:
            existing_item = session.query(Cart).filter_by(
                user_id=user_id,
                ingredient_name=ingredient_name,
                unit=unit
            ).first()

            if existing_item:
                try:
                    existing_quantity = float(existing_item.quantity) if existing_item.quantity.replace('.',
                                                                                                        '').isdigit() else 0
                    new_quantity = float(quantity) if str(quantity).replace('.', '').isdigit() else 0
                    existing_item.quantity = str(existing_quantity + new_quantity)
                except:
                    pass
            else:
                cart_item = Cart(
                    user_id=user_id,
                    ingredient_name=ingredient_name,
                    quantity=str(quantity),
                    unit=unit
                )
                session.add(cart_item)

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            return False
        finally:
            session.close()

    def remove_cart_items(self, user_id, items_to_remove):
        """Удаляет элементы из корзины в БД"""
        session = self.Session()
        try:
            removed_count = 0
            for item_data in items_to_remove:
                result = session.query(Cart).filter_by(
                    user_id=user_id,
                    ingredient_name=item_data['name'],
                    unit=item_data['unit']
                ).delete()
                removed_count += result

            session.commit()
            return removed_count > 0
        except Exception as e:
            session.rollback()
            return False
        finally:
            session.close()

    def clear_cart(self, user_id):
        """Очищает корзину пользователя в БД"""
        session = self.Session()
        try:
            deleted_count = session.query(Cart).filter_by(user_id=user_id).delete()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            return False
        finally:
            session.close()

    # ===== МЕТОДЫ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ =====

    def get_users(self, login, password):
        """Аутентификация пользователя"""
        session = self.Session()
        try:
            user = session.query(User).filter_by(login=login, password=password).first()
            if user:
                return [(user.id, user.login, user.password)]
            return []
        except Exception as e:
            return []
        finally:
            session.close()

    def register_user(self, login, password):
        """Регистрация нового пользователя"""
        session = self.Session()
        try:
            existing_user = session.query(User).filter_by(login=login).first()
            if existing_user:
                return False, "Пользователь с таким логином уже существует"

            new_user = User(login=login, password=password)
            session.add(new_user)
            session.commit()
            return True, "Пользователь успешно зарегистрирован"
        except Exception as e:
            session.rollback()
            return False, f"Ошибка при регистрации: {str(e)}"
        finally:
            session.close()

    def get_user_profile(self, user_id):
        """Получение профиля пользователя с учетом корзины"""
        session = self.Session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                recipes_count = session.query(Recipe).filter_by(user_id=user_id).count()
                favorites_count = session.query(favorites).filter_by(user_id=user_id).count()
                cart_count = session.query(Cart).filter_by(user_id=user_id).count()
                cooked_count = session.query(CookedRecipe).filter_by(user_id=user_id).count()

                return {
                    'id': user.id,
                    'login': user.login,
                    'recipes_count': recipes_count,
                    'favorites_count': favorites_count,
                    'cart_count': cart_count,
                    'cooked_count': cooked_count
                }
            return None
        except Exception as e:
            return None
        finally:
            session.close()

    # ===== МЕТОДЫ ДЛЯ РАБОТЫ С ИНГРЕДИЕНТАМИ =====
    def get_ingredients(self):
        """Получение всех ингредиентов"""
        session = self.Session()
        try:
            ingredients = session.query(Ingredient).all()
            return [(ing.id, ing.name) for ing in ingredients]
        except Exception as e:
            return []
        finally:
            session.close()

    def add_ingredient(self, name):
        """Добавление нового ингредиента"""
        session = self.Session()
        try:
            existing = session.query(Ingredient).filter_by(name=name).first()
            if existing:
                return existing.id

            new_ingredient = Ingredient(name=name)
            session.add(new_ingredient)
            session.commit()
            return new_ingredient.id
        except Exception as e:
            session.rollback()
            return None
        finally:
            session.close()

    # ===== МЕТОДЫ ДЛЯ РАБОТЫ С ИЗБРАННЫМИ РЕЦЕПТАМИ =====

    def toggle_favorite(self, user_id, recipe_id):
        """Добавление/удаление из избранного"""
        session = self.Session()
        try:
            stmt = favorites.select().where(
                (favorites.c.user_id == user_id) &
                (favorites.c.recipe_id == recipe_id)
            )
            existing = session.execute(stmt).first()

            if existing:
                stmt = favorites.delete().where(
                    (favorites.c.user_id == user_id) &
                    (favorites.c.recipe_id == recipe_id)
                )
                session.execute(stmt)
            else:
                stmt = favorites.insert().values(
                    user_id=user_id,
                    recipe_id=recipe_id
                )
                session.execute(stmt)

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            return False
        finally:
            session.close()

    def is_recipe_favorite(self, user_id, recipe_id):
        """Проверка, находится ли рецепт в избранном"""
        session = self.Session()
        try:
            stmt = favorites.select().where(
                (favorites.c.user_id == user_id) &
                (favorites.c.recipe_id == recipe_id)
            )
            result = session.execute(stmt).first()
            return result is not None
        except Exception as e:
            return False
        finally:
            session.close()

    def get_favorite_recipes(self, user_id):
        """Получает избранные рецепты пользователя"""
        session = self.Session()
        try:
            # Получаем ID избранных рецептов
            stmt = favorites.select().where(favorites.c.user_id == user_id)
            favorite_ids = [row.recipe_id for row in session.execute(stmt)]

            if not favorite_ids:
                return []

            # Получаем полные данные рецептов
            recipes = []
            for recipe_id in favorite_ids:
                recipe = session.query(Recipe).filter_by(id=recipe_id).first()
                if recipe:
                    # Собираем данные в том же формате, что и get_recipes_with_filters
                    dish_type_name = recipe.dish_type.name if recipe.dish_type else "Без категории"
                    cuisine_name = recipe.cuisine.name if recipe.cuisine else "Не указана"
                    calories = recipe.nutrition.calories if recipe.nutrition else None

                    recipe_tuple = (
                        recipe.id, recipe.user_id, recipe.name, recipe.instruction,
                        recipe.description, recipe.dish_type_id, recipe.image,
                        recipe.external_url, recipe.cook_time, dish_type_name,
                        None, calories, None, None, None, True, False,
                        cuisine_name, dish_type_name
                    )
                    recipes.append(recipe_tuple)

            return recipes
        except Exception as e:
            return []
        finally:
            session.close()

    # ===== МЕТОДЫ ДЛЯ РАБОТЫ С ПРИГОТОВЛЕННЫМИ РЕЦЕПТАМИ =====
    def mark_recipe_as_cooked(self, user_id, recipe_id, cooked=True):
        """Отмечает рецепт как приготовленный или снимает отметку"""
        session = self.Session()
        try:
            if cooked:
                existing = session.query(CookedRecipe).filter_by(
                    user_id=user_id, recipe_id=recipe_id
                ).first()
                if not existing:
                    cooked_recipe = CookedRecipe(user_id=user_id, recipe_id=recipe_id)
                    session.add(cooked_recipe)
            else:
                session.query(CookedRecipe).filter_by(
                    user_id=user_id, recipe_id=recipe_id
                ).delete()

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            return False
        finally:
            session.close()

    def is_recipe_cooked(self, user_id, recipe_id):
        """Проверяет, отмечен ли рецепт как приготовленный"""
        session = self.Session()
        try:
            cooked = session.query(CookedRecipe).filter_by(
                user_id=user_id, recipe_id=recipe_id
            ).first()
            return cooked is not None
        except Exception as e:
            return False
        finally:
            session.close()

    def get_cooked_recipes(self, user_id):
        """Получает приготовленные рецепты пользователя"""
        session = self.Session()
        try:
            cooked_recipes = session.query(CookedRecipe).filter_by(user_id=user_id).all()
            result = []
            for cooked_recipe in cooked_recipes:
                recipe = cooked_recipe.recipe
                dish_type_name = recipe.dish_type.name if recipe.dish_type else None
                cuisine_name = recipe.cuisine.name if recipe.cuisine else None
                calories = recipe.nutrition.calories if recipe.nutrition else None
                proteins = recipe.nutrition.proteins if recipe.nutrition else None
                fats = recipe.nutrition.fats if recipe.nutrition else None
                carbohydrates = recipe.nutrition.carbohydrates if recipe.nutrition else None

                recipe_tuple = (
                    recipe.id, recipe.user_id, recipe.name, recipe.instruction,
                    recipe.description, recipe.dish_type_id, recipe.image,
                    recipe.external_url, recipe.cook_time, dish_type_name,
                    None, calories, proteins, fats, carbohydrates, False, True,
                    cuisine_name, dish_type_name
                )
                result.append(recipe_tuple)
            return result
        except Exception as e:
            return []
        finally:
            session.close()

    # ===== МЕТОДЫ ДЛЯ ПОИСКА =====
    def search_recipes(self, user_id, search_term, category_filter=None):
        """Поиск рецептов по названию или ингредиентам"""
        session = self.Session()
        try:
            query = session.query(Recipe)

            if category_filter and category_filter != "Все":
                query = query.join(Category, Recipe.dish_type_id == Category.id).filter(Category.name == category_filter)

            search_query = f"%{search_term}%"
            query = query.filter(
                (Recipe.name.ilike(search_query)) |
                (Recipe.description.ilike(search_query)) |
                (Recipe.instruction.ilike(search_query))
            )

            recipes = query.all()

            result = []
            for recipe in recipes:
                dish_type_name = recipe.dish_type.name if recipe.dish_type else None
                cuisine_name = recipe.cuisine.name if recipe.cuisine else None
                calories = recipe.nutrition.calories if recipe.nutrition else None
                proteins = recipe.nutrition.proteins if recipe.nutrition else None
                fats = recipe.nutrition.fats if recipe.nutrition else None
                carbohydrates = recipe.nutrition.carbohydrates if recipe.nutrition else None

                is_favorite = session.query(favorites).filter_by(
                    user_id=user_id, recipe_id=recipe.id
                ).first() is not None

                recipe_tuple = (
                    recipe.id, recipe.user_id, recipe.name, recipe.instruction,
                    recipe.description, recipe.dish_type_id, recipe.image,
                    recipe.external_url, recipe.cook_time, dish_type_name,
                    None, calories, proteins, fats, carbohydrates, is_favorite, False,
                    cuisine_name, dish_type_name
                )
                result.append(recipe_tuple)

            return result
        except Exception as e:
            return []
        finally:
            session.close()

    def is_favorite(self, user_id, recipe_id):
        return self.is_recipe_favorite(user_id, recipe_id)
