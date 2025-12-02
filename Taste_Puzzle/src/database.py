import os
import logging
import re
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, ForeignKey, Boolean, Table, text, \
    LargeBinary, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy import inspect
from datetime import datetime
import shutil

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Базовый класс для моделей SQLAlchemy
Base = declarative_base()

# Ассоциативные таблицы для связей многие-ко-многим
# Таблица связи рецептов и категорий
recipe_categories = Table(
    'Recipe_categories', Base.metadata,
    Column('recipe_id', Integer, ForeignKey('Recipes.id'), primary_key=True),
    Column('category_id', Integer, ForeignKey('Categories.id'), primary_key=True)
)
# Таблица связи рецептов и ингредиентов
recipe_ingredients = Table(
    'Recipe_ingredients', Base.metadata,
    Column('recipe_id', Integer, ForeignKey('Recipes.id'), primary_key=True),
    Column('ingredient_id', Integer, ForeignKey('Ingredients.id'), primary_key=True),
    Column('quantity', Float, nullable=False)
)

# Таблица избранных рецептов
favorites = Table(
    'Favorites', Base.metadata,
    Column('user_id', Integer, ForeignKey('Users.id'), primary_key=True),
    Column('recipe_id', Integer, ForeignKey('Recipes.id'), primary_key=True)
)


# МОДЕЛЬ КОРЗИНЫ ДЛЯ ХРАНЕНИЯ ИНГРЕДИЕНТОВ ПОЛЬЗОВАТЕЛЯ
class Cart(Base):
    __tablename__ = 'cart'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('Users.id'), nullable=False)
    ingredient_name = Column(String(200), nullable=False)
    quantity = Column(String(50), nullable=False)  # Хранится как строка
    unit = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    # Связь с пользователем
    user = relationship("User", back_populates="cart_items")


# МОДЕЛЬ ДЛЯ ОТМЕТКИ ПРИГОТОВЛЕННЫХ РЕЦЕПТОВ
class CookedRecipe(Base):
    __tablename__ = 'cooked_recipes'

    user_id = Column(Integer, ForeignKey('Users.id'), primary_key=True)
    recipe_id = Column(Integer, ForeignKey('Recipes.id'), primary_key=True)
    cooked_at = Column(DateTime, default=datetime.now)

    # Связи с пользователем и рецептом
    user = relationship("User", back_populates="cooked_recipes")
    recipe = relationship("Recipe", back_populates="cooked_by_users")


# МОДЕЛЬ ПОЛЬЗОВАТЕЛЯ
class User(Base):
    __tablename__ = 'Users'

    id = Column(Integer, primary_key=True)
    login = Column(String(50), nullable=False)
    password = Column(String(100), nullable=False)

    # Связи с другими таблицами
    cart_items = relationship("Cart", back_populates="user")
    recipes = relationship("Recipe", back_populates="user")
    favorite_recipes = relationship("Recipe", secondary=favorites, back_populates="favorited_by")
    cooked_recipes = relationship("CookedRecipe", back_populates="user")


# МОДЕЛЬ РЕЦЕПТА
class Recipe(Base):
    __tablename__ = 'Recipes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('Users.id'), nullable=False)
    servings = Column(Integer)
    cook_time = Column(Integer)
    external_url = Column(String(500))
    image = Column(String(500)) # Хранится только имя файла изображения, например "apple_pie.jpg"
    description = Column(Text)
    instruction = Column(Text)
    name = Column(String(200), nullable=False)

    # Связи с другими таблицами
    user = relationship("User", back_populates="recipes")
    categories = relationship("Category", secondary=recipe_categories, back_populates="recipes")
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

    recipes = relationship("Recipe", secondary=recipe_categories, back_populates="categories")


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
            # Получаем абсолютный путь к директории проекта
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)

            # Пробуем разные возможные пути к базе данных
            possible_paths = [
                os.path.join(project_root, 'data', 'Taste_Pazzle.db'),
                os.path.join(project_root, 'data', 'Taste Pazzle.db'),
                os.path.join(current_dir, '..', 'data', 'Taste_Pazzle.db'),
                os.path.join(current_dir, '..', 'data', 'Taste Pazzle.db'),
            ]

            db_path = None
            for path in possible_paths:
                normalized_path = os.path.normpath(path)
                if os.path.exists(normalized_path):
                    db_path = normalized_path
                    logger.info(f"Найдена база данных: {db_path}")
                    break

            # Создание новой базы данных если файл не найден
            if not db_path:
                data_dir = os.path.join(project_root, 'data')
                os.makedirs(data_dir, exist_ok=True)

                db_path = os.path.join(data_dir, 'Taste_Pazzle.db')
                logger.warning(f"Исходная база данных не найдена. Создана новая: {db_path}")

            # Создаем движок базы данных
            self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
            self.Session = sessionmaker(bind=self.engine)

            # Создаем дополнительные таблицы если их нет
            self._create_additional_tables()

            # Проверяем и выводим информацию о существующих данных
            self._check_existing_data()

            # Мигрируем существующие данные изображений
            self.migrate_existing_images()

            # Назначаем уникальные изображения рецептам
            self.assign_unique_images_to_recipes()

            # Проверяем статус изображений
            self.check_image_status()

            logger.info("База данных успешно подключена")

        except Exception as e:
            logger.error(f"Ошибка подключения к базе данных: {e}")
            raise

    def migrate_existing_images(self):
        """Мигрирует существующие пути изображений к новому формату (только имена файлов)"""
        session = self.Session()
        try:
            recipes = session.query(Recipe).filter(Recipe.image.isnot(None)).all()
            migrated_count = 0

            for recipe in recipes:
                if recipe.image and isinstance(recipe.image, str):
                    # Если путь содержит полный путь, извлекаем только имя файла
                    if '/' in recipe.image or '\\' in recipe.image:
                        old_path = recipe.image
                        new_filename = os.path.basename(old_path)
                        recipe.image = new_filename
                        migrated_count += 1
                        logger.info(f"Мигрирован путь: {old_path} -> {new_filename}")

            if migrated_count > 0:
                session.commit()
                logger.info(f"Мигрировано {migrated_count} путей изображений")

        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка при миграции изображений: {e}")
        finally:
            session.close()

    def assign_unique_images_to_recipes(self):
        """Назначает каждому рецепту уникальное изображение на основе его названия"""
        session = self.Session()
        try:
            # Список всех доступных изображений
            available_images = [
                'apple_pie.jpg', 'cabbage_rolls.jpg', 'caesar.jpg',
                'mashed_potatoes.jpg', 'olivier.jpg', 'ramen.jpg',
                'french_toast.jpg', 'pasta_carbonara.jpg'
            ]

            # Сопоставление ключевых слов в названиях рецептов с изображениями
            keyword_mapping = {
                'яблочный пирог': 'apple_pie.jpg',
                'пирог': 'apple_pie.jpg',
                'голубцы': 'cabbage_rolls.jpg',
                'цезарь': 'caesar.jpg',
                'салат цезарь': 'caesar.jpg',
                'картофельное пюре': 'mashed_potatoes.jpg',
                'пюре': 'mashed_potatoes.jpg',
                'оливье': 'olivier.jpg',
                'салат оливье': 'olivier.jpg',
                'рамен': 'ramen.jpg',
                'французский тост': 'french_toast.jpg',
                'френч тост': 'french_toast.jpg',
                'карбонара': 'pasta_carbonara.jpg',
                'паста карбонара': 'pasta_carbonara.jpg'
            }

            # Получаем все рецепты
            recipes = session.query(Recipe).all()
            logger.info(f"Найдено {len(recipes)} рецептов для назначения изображений")

            # Создаем копию списка доступных изображений для отслеживания использованных
            used_images = set()
            updated_count = 0

            # Сначала назначаем изображения по точному соответствию
            for recipe in recipes:
                recipe_name_lower = recipe.name.lower()
                image_assigned = False

                # Ищем точное соответствие по ключевым словам
                for keyword, image_file in keyword_mapping.items():
                    if keyword in recipe_name_lower and image_file not in used_images:
                        recipe.image = image_file
                        used_images.add(image_file)
                        updated_count += 1
                        image_assigned = True
                        logger.info(f"Назначено изображение по ключевому слову: '{recipe.name}' -> {image_file}")
                        break

                # Если не нашли точное соответствие, ищем частичное
                if not image_assigned:
                    for image_file in available_images:
                        if image_file not in used_images:
                            # Проверяем базовое соответствие по имени файла и названию рецепта
                            file_base = os.path.splitext(image_file)[0].lower()
                            file_base_clean = file_base.replace('_', ' ').replace('-', ' ')

                            if (file_base_clean in recipe_name_lower or
                                    any(word in recipe_name_lower for word in file_base_clean.split())):
                                recipe.image = image_file
                                used_images.add(image_file)
                                updated_count += 1
                                image_assigned = True
                                logger.info(
                                    f"Назначено изображение по частичному соответствию: '{recipe.name}' -> {image_file}")
                                break

            # Для оставшихся рецептов назначаем оставшиеся изображения
            recipes_without_images = [r for r in recipes if not r.image]
            remaining_images = [img for img in available_images if img not in used_images]

            for i, recipe in enumerate(recipes_without_images):
                if i < len(remaining_images):
                    recipe.image = remaining_images[i]
                    updated_count += 1
                    logger.info(f"Назначено оставшееся изображение: '{recipe.name}' -> {remaining_images[i]}")
                else:
                    logger.warning(f"Не осталось изображений для рецепта: '{recipe.name}'")

            session.commit()
            logger.info(f"Назначено {updated_count} изображений рецептам")

            # Проверяем результат
            self._verify_image_assignments()

        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка при назначении изображений рецептам: {e}")
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

            # Логируем результаты
            logger.info("=== ПРОВЕРКА НАЗНАЧЕНИЯ ИЗОБРАЖЕНИЙ ===")
            for image_file, count in image_count.items():
                status = "OK" if count == 1 else "ПОВТОР"
                logger.info(f"{image_file}: {count} рецептов - {status}")

            # Проверяем рецепты без изображений
            recipes_without_images = [r for r in recipes if not r.image]
            if recipes_without_images:
                logger.warning(f"Рецепты без изображений: {len(recipes_without_images)}")
                for recipe in recipes_without_images:
                    logger.warning(f"  - {recipe.name}")

        except Exception as e:
            logger.error(f"Ошибка при проверке назначения изображений: {e}")
        finally:
            session.close()

    def check_image_status(self):
        """Проверяет статус изображений в базе данных"""
        session = self.Session()
        try:
            # Общее количество рецептов
            total_recipes = session.query(Recipe).count()

            # Рецепты с изображениями
            recipes_with_images = session.query(Recipe).filter(Recipe.image.isnot(None)).all()

            # Проверяем доступность файлов изображений
            available_images = 0
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            images_dir = os.path.join(project_root, 'img', 'recipe_img')

            for recipe in recipes_with_images:
                if recipe.image and isinstance(recipe.image, str):
                    image_path = os.path.join(images_dir, recipe.image)
                    if os.path.exists(image_path):
                        available_images += 1

            logger.info(f"=== СТАТУС ИЗОБРАЖЕНИЙ ===")
            logger.info(f"Всего рецептов: {total_recipes}")
            logger.info(f"Рецептов с именами изображений: {len(recipes_with_images)}")
            logger.info(f"Доступных файлов изображений: {available_images}")

            # Выводим информацию о всех рецептах
            recipes = session.query(Recipe).all()
            for recipe in recipes:
                if recipe.image:
                    image_path = os.path.join(images_dir, recipe.image)
                    status = "Есть файл" if os.path.exists(image_path) else "Файл не найден"
                else:
                    status = "Нет изображения"
                logger.info(f"Рецепт {recipe.id}: '{recipe.name}' -> {recipe.image} - {status}")

        except Exception as e:
            logger.error(f"Ошибка проверки статуса изображений: {e}")
        finally:
            session.close()

    def _create_additional_tables(self):
        """Создает дополнительные таблицы если они не существуют"""
        try:
            inspector = inspect(self.engine)
            existing_tables = [table.lower() for table in inspector.get_table_names()]

            if 'cart' not in existing_tables:
                Base.metadata.tables['cart'].create(self.engine)
                logger.info("Таблица корзины создана")

            if 'cooked_recipes' not in existing_tables:
                Base.metadata.tables['cooked_recipes'].create(self.engine)
                logger.info("Таблица приготовленных рецептов создана")

        except Exception as e:
            logger.error(f"Ошибка создания дополнительных таблиц: {e}")
            raise

    def _check_existing_data(self):
        """Проверяет и выводит информацию о существующих данных в БД"""
        session = self.Session()
        try:
            # Проверяем количество записей в основных таблицах
            users_count = session.query(User).count()
            recipes_count = session.query(Recipe).count()
            categories_count = session.query(Category).count()
            ingredients_count = session.query(Ingredient).count()

            logger.info(f"Количество пользователей в БД: {users_count}")
            logger.info(f"Количество рецептов в БД: {recipes_count}")
            logger.info(f"Количество категорий в БД: {categories_count}")
            logger.info(f"Количество ингредиентов в БД: {ingredients_count}")

            # Выводим первых 5 пользователей для отладки
            users = session.query(User).limit(5).all()
            for user in users:
                logger.info(f"Пользователь: id={user.id}, login={user.login}")

        except Exception as e:
            logger.error(f"Ошибка при проверке данных БД: {e}")
        finally:
            session.close()

    def get_recipe_image(self, recipe_id):
        """Получение изображения рецепта по имени файла из БД"""
        try:
            session = self.Session()
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()

            if not recipe:
                logger.warning(f"Рецепт с ID {recipe_id} не найден")
                session.close()
                return self._create_text_pixmap("Рецепт не найден")

            if recipe and recipe.image:
                # recipe.image содержит только имя файла, например "apple_pie.jpg"
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(current_dir)
                images_dir = os.path.join(project_root, 'img', 'recipe_img')

                # Пробуем разные возможные пути
                possible_paths = [
                    os.path.join(images_dir, recipe.image),
                    os.path.join(project_root, 'img', 'recipe_img', recipe.image),
                    os.path.join(current_dir, '..', 'img', 'recipe_img', recipe.image),
                ]

                for path in possible_paths:
                    normalized_path = os.path.normpath(path)
                    if os.path.exists(normalized_path):
                        from PyQt6.QtGui import QPixmap
                        pixmap = QPixmap(normalized_path)
                        if not pixmap.isNull():
                            session.close()
                            return pixmap

                logger.warning(f"Файл изображения не найден для рецепта {recipe_id}: {recipe.image}")

            # Создаем текстовую заглушку с названием рецепта
            session.close()
            return self._create_text_pixmap(recipe.name if recipe else "Без названия")

        except Exception as e:
            logger.error(f"Ошибка получения изображения для рецепта {recipe_id}: {e}")
            if 'session' in locals():
                session.close()
            return self._create_text_pixmap("Ошибка")

    def _create_text_pixmap(self, text):
        """Создает QPixmap с текстовой заглушкой"""
        from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
        from PyQt6.QtCore import Qt

        # Создаем pixmap
        pixmap = QPixmap(200, 150)
        pixmap.fill(QColor(240, 240, 240))  # Светло-серый фон

        # Создаем painter для рисования текста
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Настраиваем шрифт
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)

        # Настраиваем цвет текста
        painter.setPen(QColor(100, 100, 100))

        # Рисуем текст
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()

        return pixmap

    def _parse_quantity(self, quantity_str):
        """Парсит количество из строки в числовое значение и определяет единицу измерения"""
        try:
            if isinstance(quantity_str, (int, float)):
                return float(quantity_str), 'г'

            # Пытаемся извлечь число из строки
            numbers = re.findall(r'\d+\.?\d*', str(quantity_str))
            if numbers:
                quantity = float(numbers[0])
                # Определяем единицу измерения на основе текста
                unit = 'г'  # единица по умолчанию
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
                # Если не нашли число, возвращаем 1 и исходную строку как единицу
                return 1.0, str(quantity_str)

        except Exception as e:
            logger.error(f"Ошибка парсинга количества '{quantity_str}': {e}")
            return 1.0, 'шт'

    # Методы для работы с корзиной
    def get_cart_items(self, user_id):
        """Получает все элементы корзины для пользователя из БД"""
        session = self.Session()
        try:
            items = session.query(Cart).filter_by(user_id=user_id).all()
            logger.info(f"Загружено {len(items)} элементов корзины для пользователя {user_id}")
            return [{
                'name': item.ingredient_name,
                'quantity': item.quantity,
                'unit': item.unit
            } for item in items]
        except Exception as e:
            logger.error(f"Ошибка получения корзины: {e}")
            return []
        finally:
            session.close()

    def add_cart_item(self, user_id, ingredient_name, quantity, unit):
        """Добавляет элемент в корзину в БД"""
        session = self.Session()
        try:
            # Проверяем, нет ли уже такого ингредиента в корзине
            existing_item = session.query(Cart).filter_by(
                user_id=user_id,
                ingredient_name=ingredient_name,
                unit=unit
            ).first()

            if existing_item:
                # Если уже есть, обновляем количество
                try:
                    # Пытаемся сложить количества
                    existing_quantity = float(existing_item.quantity) if existing_item.quantity.replace('.',
                                                                                                        '').isdigit() else 0
                    new_quantity = float(quantity) if str(quantity).replace('.', '').isdigit() else 0
                    existing_item.quantity = str(existing_quantity + new_quantity)
                except:
                    # Если не получается сложить, оставляем как есть
                    pass
            else:
                # Если нет, создаем новый элемент
                cart_item = Cart(
                    user_id=user_id,
                    ingredient_name=ingredient_name,
                    quantity=str(quantity),
                    unit=unit
                )
                session.add(cart_item)

            session.commit()
            logger.info(f"Добавлен элемент в корзину: {ingredient_name} - {quantity} {unit}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка добавления в корзину: {e}")
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
            logger.info(f"Удалено {removed_count} элементов из корзины")
            return removed_count > 0
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка удаления из корзины: {e}")
            return False
        finally:
            session.close()

    def clear_cart(self, user_id):
        """Очищает корзину пользователя в БД"""
        session = self.Session()
        try:
            deleted_count = session.query(Cart).filter_by(user_id=user_id).delete()
            session.commit()
            logger.info(f"Очищена корзина пользователя {user_id}, удалено {deleted_count} элементов")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка очистки корзины: {e}")
            return False
        finally:
            session.close()

    # Методы для работы с пользователями
    def get_users(self, login, password):
        """Аутентификация пользователя"""
        session = self.Session()
        try:
            user = session.query(User).filter_by(login=login, password=password).first()
            if user:
                return [(user.id, user.login, user.password)]
            return []
        except Exception as e:
            logger.error(f"Ошибка аутентификации: {e}")
            return []
        finally:
            session.close()

    def register_user(self, login, password):
        """Регистрация нового пользователя"""
        session = self.Session()
        try:
            # Проверка существования пользователя
            existing_user = session.query(User).filter_by(login=login).first()
            if existing_user:
                return False, "Пользователь с таким логином уже существует"

            new_user = User(login=login, password=password)
            session.add(new_user)
            session.commit()
            return True, "Пользователь успешно зарегистрирован"
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка регистрации: {e}")
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
            logger.error(f"Ошибка получения профиля: {e}")
            return None
        finally:
            session.close()

    # Методы для работы с кухнями
    def get_cuisines(self):
        """Получение всех кухонь (категорий с типом 'cuisine')"""
        session = self.Session()
        try:
            cuisines = session.query(Category).filter_by(type='cuisine').all()
            return [(cat.id, cat.name) for cat in cuisines]
        except Exception as e:
            logger.error(f"Ошибка получения кухонь: {e}")
            return []
        finally:
            session.close()

    # Методы для работы с рецептами
    def get_categories(self):
        """Получение всех категорий"""
        session = self.Session()
        try:
            categories = session.query(Category).all()
            return [(cat.id, cat.name, cat.type) for cat in categories]
        except Exception as e:
            logger.error(f"Ошибка получения категорий: {e}")
            return []
        finally:
            session.close()

    def get_ingredients(self):
        """Получение всех ингредиентов"""
        session = self.Session()
        try:
            ingredients = session.query(Ingredient).all()
            return [(ing.id, ing.name) for ing in ingredients]
        except Exception as e:
            logger.error(f"Ошибка получения ингредиентов: {e}")
            return []
        finally:
            session.close()

    def get_recipes_with_filters(self, user_id, cuisine=None, max_time=None,
                                 favorites_only=False, cooked_only=False,
                                 ingredient_filter=None, name_filter=None):
        """Получение рецептов с фильтрами с группировкой по типам блюд"""
        session = self.Session()
        try:
            # Базовый запрос - все рецепты
            query = session.query(Recipe).distinct()

            logger.info(f"=== НАЧАЛО ФИЛЬТРАЦИИ ===")
            logger.info(
                f"Фильтры: кухня={cuisine}, время={max_time}, избранное={favorites_only}, "
                f"приготовлено={cooked_only}, ингредиенты={ingredient_filter}, название={name_filter}"
            )

            # Фильтр по кухне
            if cuisine and cuisine != "Любая кухня":
                logger.info(f"Применяем фильтр по кухне: {cuisine}")
                cuisine_category = session.query(Category).filter(
                    Category.name == cuisine,
                    Category.type == 'cuisine'
                ).first()

                if cuisine_category:
                    logger.info(f"Найдена категория кухни: id={cuisine_category.id}, name={cuisine_category.name}")
                    subquery = session.query(recipe_categories.c.recipe_id).filter(
                        recipe_categories.c.category_id == cuisine_category.id
                    ).subquery()
                    query = query.filter(Recipe.id.in_(subquery))

            # Фильтр по времени приготовления
            if max_time:
                query = query.filter(Recipe.cook_time <= max_time)
                logger.info(f"Применен фильтр по времени: <= {max_time} мин")

            # Фильтр по избранному
            if favorites_only:
                query = query.join(Recipe.favorited_by).filter(User.id == user_id)
                logger.info("Применен фильтр: Только избранное")

            # Фильтр по приготовленным рецептам
            if cooked_only:
                cooked_subquery = session.query(CookedRecipe.recipe_id).filter_by(user_id=user_id).subquery()
                query = query.filter(Recipe.id.in_(cooked_subquery))
                logger.info("Применен фильтр: Только приготовленные")

            # Фильтр по названию
            if name_filter and name_filter.strip():
                search_term = f"%{name_filter}%"
                query = query.filter(Recipe.name.ilike(search_term))
                logger.info(f"Применен фильтр по названию: {name_filter}")

            # Фильтр по ингредиентам
            if ingredient_filter and ingredient_filter.strip():
                logger.info(f"Применяем фильтр по ингредиентам: {ingredient_filter}")
                ingredients_list = [ing.strip() for ing in ingredient_filter.split(',') if ing.strip()]

                for ing_name in ingredients_list:
                    matching_ingredients = session.query(Ingredient).filter(
                        Ingredient.name.ilike(f'%{ing_name}%')
                    ).all()

                    if matching_ingredients:
                        ing_ids = [ing.id for ing in matching_ingredients]
                        ing_subquery = session.query(recipe_ingredients.c.recipe_id).filter(
                            recipe_ingredients.c.ingredient_id.in_(ing_ids)
                        ).subquery()
                        query = query.filter(Recipe.id.in_(ing_subquery))
                    else:
                        logger.info(f"Ингредиенты по запросу '{ing_name}' не найдены")
                        return {}

            # Выполняем запрос
            recipes = query.all()
            logger.info(f"Найдено рецептов после фильтрации: {len(recipes)}")

            # Группируем рецепты по типам блюд
            grouped_recipes = {
                "Салаты": [],
                "Десерты": [],
                "Основные блюда": [],
                "Завтраки": [],
                "Гарниры": [],
                "Супы": []
            }

            for recipe in recipes:
                # Получаем тип блюда из категорий рецепта
                dish_type = None
                for cat in recipe.categories:
                    if cat.type == 'dish_type':
                        dish_type = cat.name
                        break

                # Если тип блюда найден и есть в нашей группировке
                if dish_type and dish_type in grouped_recipes:
                    # Получаем кухню
                    cuisine_name = None
                    for cat in recipe.categories:
                        if cat.type == 'cuisine':
                            cuisine_name = cat.name
                            break

                    # Данные о питательности
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

                    recipe_tuple = (
                        recipe.id,
                        recipe.user_id,
                        recipe.name,
                        recipe.instruction,
                        recipe.description,
                        None,  # Зарезервировано
                        recipe.image,
                        recipe.external_url,
                        recipe.cook_time,
                        dish_type,  # Тип блюда (как основная категория для совместимости)
                        None,
                        calories,
                        proteins,
                        fats,
                        carbohydrates,
                        is_favorite,
                        is_cooked,
                        cuisine_name,  # Кухня
                        dish_type  # Тип блюда
                    )

                    grouped_recipes[dish_type].append(recipe_tuple)

            # Удаляем пустые группы
            grouped_recipes = {k: v for k, v in grouped_recipes.items() if v}

            logger.info(f"=== КОНЕЦ ФИЛЬТРАЦИИ ===")
            logger.info(f"Группировка: {', '.join([f'{k}: {len(v)}' for k, v in grouped_recipes.items()])}")

            return grouped_recipes

        except Exception as e:
            logger.error(f"Ошибка получения рецептов: {e}", exc_info=True)
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
            logger.error(f"Ошибка получения ингредиентов рецепта: {e}")
            return []
        finally:
            session.close()

    def _save_recipe_image(self, image_data, recipe_id, recipe_name):
        """Сохраняет изображение рецепта с уникальным именем и возвращает имя файла"""
        try:
            # Создаем папку для изображений рецептов если её нет
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            images_dir = os.path.join(project_root, 'img', 'recipe_img')
            os.makedirs(images_dir, exist_ok=True)

            # Генерируем безопасное имя файла на основе названия рецепта
            safe_name = re.sub(r'[^\w\s-]', '', recipe_name).strip().lower()
            safe_name = re.sub(r'[-\s]+', '_', safe_name)

            # Создаем уникальное имя файла с ID рецепта
            image_filename = f"{safe_name}_{recipe_id}.jpg"
            image_path = os.path.join(images_dir, image_filename)

            # Если переданы бинарные данные, сохраняем в файл
            if isinstance(image_data, bytes):
                with open(image_path, 'wb') as f:
                    f.write(image_data)
            # Если передан путь к файлу, копируем его
            elif isinstance(image_data, str) and os.path.exists(image_data):
                shutil.copy2(image_data, image_path)
            else:
                logger.warning(f"Неизвестный тип данных изображения: {type(image_data)}")
                return None

            logger.info(f"Изображение сохранено: {image_filename}")
            return image_filename  # Возвращаем только имя файла

        except Exception as e:
            logger.error(f"Ошибка сохранения изображения рецепта: {e}")
            return None

    def add_recipe(self, user_id, name, instruction, description, category_id,
                   cook_time, ingredients_list, nutrition_data, image=None):
        """Добавление нового рецепта"""
        session = self.Session()
        try:
            # Сначала создаем рецепт без изображения
            new_recipe = Recipe(
                user_id=user_id,
                name=name,
                instruction=instruction,
                description=description,
                cook_time=cook_time
            )
            session.add(new_recipe)
            session.flush()  # Получаем ID рецепта

            # Обрабатываем изображение если оно есть
            image_filename = None
            if image:
                image_filename = self._save_recipe_image(image, new_recipe.id, name)
                new_recipe.image = image_filename

            # Добавляем категорию
            if category_id:
                recipe_category = recipe_categories.insert().values(
                    recipe_id=new_recipe.id,
                    category_id=category_id
                )
                session.execute(recipe_category)

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
            logger.info(f"Рецепт '{name}' успешно добавлен с ID {new_recipe.id}")
            return new_recipe.id

        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка добавления рецепта: {e}")
            return None
        finally:
            session.close()

    def update_recipe(self, recipe_id, name, instruction, description, category_id,
                      cook_time, ingredients_list, nutrition_data, image=None):
        """Обновление существующего рецепта"""
        session = self.Session()
        try:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                logger.error(f"Рецепт с ID {recipe_id} не найден")
                return False

            # Обновляем основные данные
            recipe.name = name
            recipe.instruction = instruction
            recipe.description = description
            recipe.cook_time = cook_time

            # Обрабатываем изображение если оно есть
            if image:
                image_filename = self._save_recipe_image(image, recipe_id, name)
                recipe.image = image_filename

            # Обновляем категорию
            session.execute(
                recipe_categories.delete().where(recipe_categories.c.recipe_id == recipe_id)
            )
            if category_id:
                session.execute(
                    recipe_categories.insert().values(
                        recipe_id=recipe_id,
                        category_id=category_id
                    )
                )

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
            logger.info(f"Рецепт с ID {recipe_id} успешно обновлен")
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка обновления рецепта: {e}")
            return False
        finally:
            session.close()

    def delete_recipe(self, recipe_id):
        """Удаление рецепта"""
        session = self.Session()
        try:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if recipe:
                # Удаляем связанные записи
                session.execute(
                    recipe_categories.delete().where(recipe_categories.c.recipe_id == recipe_id)
                )
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

                # Удаляем файл изображения если он существует
                if recipe.image and isinstance(recipe.image, str):
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    project_root = os.path.dirname(current_dir)
                    image_path = os.path.join(project_root, 'img', 'recipe_img', recipe.image)
                    if os.path.exists(image_path):
                        os.remove(image_path)

                # Удаляем сам рецепт
                session.delete(recipe)
                session.commit()
                logger.info(f"Рецепт с ID {recipe_id} успешно удален")
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка удаления рецепта: {e}")
            return False
        finally:
            session.close()

    # Методы для работы с избранными рецептами
    def toggle_favorite(self, user_id, recipe_id):
        """Добавление/удаление из избранного"""
        session = self.Session()
        try:
            # Проверяем, есть ли уже в избранном
            stmt = favorites.select().where(
                (favorites.c.user_id == user_id) &
                (favorites.c.recipe_id == recipe_id)
            )
            existing = session.execute(stmt).first()

            if existing:
                # Удаляем из избранного
                stmt = favorites.delete().where(
                    (favorites.c.user_id == user_id) &
                    (favorites.c.recipe_id == recipe_id)
                )
                session.execute(stmt)
            else:
                # Добавляем в избранное
                stmt = favorites.insert().values(
                    user_id=user_id,
                    recipe_id=recipe_id
                )
                session.execute(stmt)

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка переключения избранного: {e}")
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
            logger.error(f"Ошибка проверки избранного: {e}")
            return False
        finally:
            session.close()

    def get_favorite_recipes(self, user_id):
        """Получение избранных рецептов"""
        session = self.Session()
        try:
            stmt = favorites.select().where(favorites.c.user_id == user_id)
            favorite_ids = [row.recipe_id for row in session.execute(stmt)]

            recipes = session.query(Recipe).filter(Recipe.id.in_(favorite_ids)).all()

            result = []
            for recipe in recipes:
                main_category = recipe.categories[0].name if recipe.categories else None
                calories = recipe.nutrition.calories if recipe.nutrition else None
                proteins = recipe.nutrition.proteins if recipe.nutrition else None
                fats = recipe.nutrition.fats if recipe.nutrition else None
                carbohydrates = recipe.nutrition.carbohydrates if recipe.nutrition else None

                recipe_tuple = (
                    recipe.id, recipe.user_id, recipe.name, recipe.instruction,
                    recipe.description, None, recipe.image,
                    recipe.external_url, recipe.cook_time, main_category,
                    None, calories, proteins, fats, carbohydrates, True, False
                )
                result.append(recipe_tuple)

            return result
        except Exception as e:
            logger.error(f"Ошибка получения избранных рецептов: {e}")
            return []
        finally:
            session.close()

    # Методы для работы с приготовленными рецептами
    def mark_recipe_as_cooked(self, user_id, recipe_id, cooked=True):
        """Отмечает рецепт как приготовленный или снимает отметку"""
        session = self.Session()
        try:
            if cooked:
                # Проверяем, не отмечен ли уже рецепт
                existing = session.query(CookedRecipe).filter_by(
                    user_id=user_id, recipe_id=recipe_id
                ).first()
                if not existing:
                    cooked_recipe = CookedRecipe(user_id=user_id, recipe_id=recipe_id)
                    session.add(cooked_recipe)
            else:
                # Снимаем отметку
                session.query(CookedRecipe).filter_by(
                    user_id=user_id, recipe_id=recipe_id
                ).delete()

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка отметки рецепта как приготовленного: {e}")
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
            logger.error(f"Ошибка проверки статуса приготовления: {e}")
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
                main_category = recipe.categories[0].name if recipe.categories else None
                calories = recipe.nutrition.calories if recipe.nutrition else None
                proteins = recipe.nutrition.proteins if recipe.nutrition else None
                fats = recipe.nutrition.fats if recipe.nutrition else None
                carbohydrates = recipe.nutrition.carbohydrates if recipe.nutrition else None

                recipe_tuple = (
                    recipe.id, recipe.user_id, recipe.name, recipe.instruction,
                    recipe.description, None, recipe.image,
                    recipe.external_url, recipe.cook_time, main_category,
                    None, calories, proteins, fats, carbohydrates, False, True
                )
                result.append(recipe_tuple)
            return result
        except Exception as e:
            logger.error(f"Ошибка получения приготовленных рецептов: {e}")
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
            logger.error(f"Ошибка добавления ингредиента: {e}")
            return None
        finally:
            session.close()

    def search_recipes(self, user_id, search_term, category_filter=None):
        """Поиск рецептов по названию или ингредиентам"""
        session = self.Session()
        try:
            query = session.query(Recipe)

            # Фильтр по категории
            if category_filter and category_filter != "Все":
                query = query.join(Recipe.categories).filter(Category.name == category_filter)

            # Поиск по названию, описанию или инструкциям
            search_query = f"%{search_term}%"
            query = query.filter(
                (Recipe.name.ilike(search_query)) |
                (Recipe.description.ilike(search_query)) |
                (Recipe.instruction.ilike(search_query))
            )

            recipes = query.all()

            # Формирование результата
            result = []
            for recipe in recipes:
                main_category = recipe.categories[0].name if recipe.categories else None
                calories = recipe.nutrition.calories if recipe.nutrition else None
                proteins = recipe.nutrition.proteins if recipe.nutrition else None
                fats = recipe.nutrition.fats if recipe.nutrition else None
                carbohydrates = recipe.nutrition.carbohydrates if recipe.nutrition else None

                is_favorite = session.query(favorites).filter_by(
                    user_id=user_id, recipe_id=recipe.id
                ).first() is not None

                recipe_tuple = (
                    recipe.id, recipe.user_id, recipe.name, recipe.instruction,
                    recipe.description, None, recipe.image,
                    recipe.external_url, recipe.cook_time, main_category,
                    None, calories, proteins, fats, carbohydrates, is_favorite, False
                )
                result.append(recipe_tuple)

            return result
        except Exception as e:
            logger.error(f"Ошибка при поиске рецептов: {e}")
            return []
        finally:
            session.close()