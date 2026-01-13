# ruff: noqa: W505, E501
# mypy: disable-error-code="name-defined,valid-type,type-arg,attr-defined,assignment,arg-type,misc,call-overload,call-arg"
"""Базовый репозиторий sqlalchemy."""

from datetime import datetime
from typing import Any, Literal

from sqlalchemy import (
    BinaryExpression,
    Select,
    UniqueConstraint,
    and_,
    delete,
    func,
    inspect,
    not_,
    or_,
    update,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import select

from axiom_sqlalchemy.database.postgres.base import Base
from axiom_core.dto.scheme.request.filter import FilterRequest
from axiom_core.dto.type.filter import FilterType
from axiom_core.dto.type.query import QueryOperator
from axiom_core.dto.type.sort import SortTypeEnum
from axiom_core.exception import BadRequestException, FieldException, NotFoundException
from axiom_core.repository import BaseRepository


class SQLAlchemyRepository[
    ModelType: Base,
    SessionType: AsyncSession,
    QueryType: Select,
](BaseRepository):
    """Базовый класс для репозиториев данных sqlalchemy."""

    model_class: type[ModelType]
    session: type[SessionType]

    async def create(self, attributes: dict[str, Any]) -> ModelType:
        """Создает экземпляр модели.

        Args:
            attributes: Атрибуты для создания модели.

        Returns:
            Созданный экземпляр модели.
        """
        created_model = self.model_class(**attributes)
        self.session.add(created_model)
        return created_model

    async def create_model(self, model: ModelType) -> ModelType:
        """Создает экземпляр модели.

        Args:
            model: Модель базы данных.

        Returns:
            Созданный экземпляр модели.
        """
        self.session.add(model)
        return model

    async def create_many(
        self,
        attributes_list: list[dict[str, Any]],
    ) -> list[ModelType]:
        """Создает несколько экземпляров модели за раз."""
        if not attributes_list:
            return []

        models = []
        for attributes in attributes_list:
            created_model = self.model_class(**attributes)
            models.append(created_model)
            self.session.add(created_model)

        return models

    async def update(self, model: ModelType, attributes: dict[str, Any]) -> ModelType:
        """Обновляет экземпляр модели с заданными атрибутами.

        Args:
            model: Модель для обновления.
            attributes: Атрибуты для обновления экземпляра модели.

        Returns:
            Обновленный экземпляр модели.
        """
        if model is None:
            raise NotFoundException("Entity not found")
        for field, value in attributes.items():
            self._validate_params(field=field, value=value)
            setattr(model, field, value)
        await self.session.flush()

        return model

    async def delete(self, model: ModelType) -> ModelType:
        """Удаляет экземпляр модели.

        Args:
            model: Модель для удаления.

        Returns:
            Удаленный экземпляр модели.
        """
        if model is None:
            raise NotFoundException("Entity not found")
        await self.session.delete(model)
        return model

    async def update_by_filters(
        self,
        filter_request: FilterRequest,
        attributes: dict[str, Any],
        unique: bool = False,
    ) -> ModelType | None | list[ModelType]:
        """Обновляет экземпляры модели по фильтрам.

        Args:
           filter_request: Фильтры для поиска.
           attributes: Атрибуты для обновления экземпляров модели.
           unique: Флаг, что ожидается ровно одна запись (или ни одной).

        Returns:
            Обновлённые экземпляры модели.
        """
        return await self._modify_by_filters(
            filter_request=filter_request,
            attributes=attributes,
            op="update",
            unique=unique,
        )

    async def update_by(
        self,
        field: str,
        value: Any,
        attributes: dict[str, Any],
        operator: QueryOperator = QueryOperator.EQUALS,
        unique: bool = False,
    ) -> ModelType | None | list[ModelType]:
        """Обновляет сущности, найденные по заданному условию, за один запрос.

        Args:
            field: Поле для поиска.
            value: Значение для поиска.
            attributes: Словарь {поле: значение} для обновления.
            operator: Оператор сравнения (по умолчанию EQUALS).
            unique: Флаг, что ожидается ровно одна запись (или ни одной).

        Returns:
            - Если unique=True, возвращается одна обновлённая сущность или None,
              если ничего не найдено.
            - Если unique=False, возвращается список всех обновлённых сущностей
              (включая пустой список, если ничего не найдено).
        """
        return await self._modify_by(
            field=field,
            value=value,
            attributes=attributes,
            operator=operator,
            op="update",
            unique=unique,
        )

    async def delete_by_filters(
        self,
        filter_request: FilterRequest,
        unique: bool = False,
    ) -> ModelType | None | list[ModelType]:
        """Удаляет экземпляры модели по фильтрам.

        Args:
           filter_request: Фильтры для поиска.
           unique: Флаг, что ожидается ровно одна запись (или ни одной).

        Returns:
            Удалённые экземпляры модели.
        """
        return await self._modify_by_filters(
            filter_request=filter_request,
            op="delete",
            unique=unique,
        )

    async def delete_by(
        self,
        field: str,
        value: Any,
        operator: QueryOperator = QueryOperator.EQUALS,
        unique: bool = False,
    ) -> ModelType | None | list[ModelType]:
        """Удаляет сущности, найденные по заданному условию, за один запрос.

        Args:
            field: Поле для поиска.
            value: Значение для поиска.
            operator: Оператор сравнения (по умолчанию EQUALS).
            unique: Флаг, что ожидается ровно одна запись (или ни одной).

        Returns:
            - Если unique=True, возвращается одна удаленная сущность или None,
              если ничего не найдено.
            - Если unique=False, возвращается список всех удаленных сущностей
              (включая пустой список, если ничего не найдено).
        """
        return await self._modify_by(
            field=field,
            value=value,
            op="delete",
            operator=operator,
            unique=unique,
        )

    async def create_or_update_by(
        self,
        attributes: dict[str, Any],
        update_fields: list[str] | None = None,
    ) -> ModelType:
        """Создать или обновить модель."""
        for f, v in attributes.items():
            self._validate_params(field=f, value=v)

        conflict_cols = self._get_conflict_fields()

        if not conflict_cols:
            return await self.create(attributes)
        else:
            stmt = pg_insert(self.model_class).values(**attributes)
            stmt = stmt.on_conflict_do_update(
                index_elements=conflict_cols,
                set_={
                    field: attributes[field]
                    for field in (update_fields or attributes.keys())
                    if attributes.get(field) is not None
                },
            ).returning(self.model_class)

        select_stmt = self._query().from_statement(stmt)
        return await self._one_or_none(select_stmt)  # type: ignore[return-value]

    def _query(self) -> Select:
        """Возвращает вызываемый объект, который можно использовать для запроса модели.

        Returns:
            Вызываемый объект, который можно использовать для запроса модели.
        """
        query = select(self.model_class)

        return query

    def _maybe_join(self, query: Select, field: str) -> Select:
        """Возвращает запрос, который может указать на использование связанной сущности.

        Returns:
            Запрос со связанной сущностью.
        """
        if "." in field:
            rel_name, _ = field.split(".", 1)
            rel_attr = getattr(self.model_class, rel_name, None)
            if rel_attr is None:
                raise BadRequestException(
                    f"{self.model_class.__name__} has no relation {rel_name}",
                )
            return query.join(rel_attr)
        return query

    def _get_by[BinaryExpression](
        self,
        field: str,
        value: Any,
        operator: QueryOperator = QueryOperator.EQUALS,
    ) -> BinaryExpression:  # type: ignore[type-var]
        """Возвращает запрос, отфильтрованный по указанной колонке.

        Args:
            field: Колонка для фильтрации.
            value: Значение для фильтрации.
            operator: Оператор сравнения field и value.

        Returns:
            Отфильтрованный запрос.
        """
        if "." in field:
            rel_name, col_name = field.split(".", 1)
            # получаем класс связанной сущности
            try:
                rel_prop = getattr(self.model_class, rel_name).property
                target_cls = rel_prop.mapper.class_
            except Exception as exc:
                raise BadRequestException(f"Wrong relation name: {rel_name}") from exc

            column = getattr(target_cls, col_name, None)
            if column is None:
                raise BadRequestException(
                    f"{target_cls.__name__} has no column {col_name}",
                )
            # теперь возвращаем условие на связанную сущность
            left = column
        else:
            # обычное поле той же модели
            if not hasattr(self.model_class, field):
                raise BadRequestException(
                    f"{self.model_class.__name__} has no field {field}",
                )
            left = getattr(self.model_class, field)

        # и сравниваем через оператор
        match operator:
            case QueryOperator.IN:
                if not isinstance(value, list | tuple | set):
                    raise BadRequestException(
                        f"Value for IN must be a list, tuple or set, got {type(value).__name__}",
                    )
                return left.in_(value)

            case QueryOperator.NOT_IN:
                if not isinstance(value, list | tuple | set):
                    raise BadRequestException(
                        f"Value for NOT_IN must be a list, tuple or set, got {type(value).__name__}",
                    )
                return not_(left.in_(value))

            case QueryOperator.EQUALS:
                return left == value

            case QueryOperator.NOT_EQUAL:
                return left != value

            case QueryOperator.GREATER:
                return left > value

            case QueryOperator.EQUALS_OR_GREATER:
                return left >= value

            case QueryOperator.LESS:
                return left < value

            case QueryOperator.EQUALS_OR_LESS:
                return left <= value

            case QueryOperator.STARTS_WITH:
                if not isinstance(value, str):
                    raise BadRequestException(
                        f"Value for STARTS_WITH must be a string, got {type(value).__name__}",
                    )
                return left.startswith(value)

            case QueryOperator.NOT_START_WITH:
                if not isinstance(value, str):
                    raise BadRequestException(
                        f"Value for NOT_START_WITH must be a string, got {type(value).__name__}",
                    )
                return not_(left.startswith(value))

            case QueryOperator.ENDS_WITH:
                if not isinstance(value, str):
                    raise BadRequestException(
                        f"Value for ENDS_WITH must be a string, got {type(value).__name__}",
                    )
                return left.endswith(value)

            case QueryOperator.NOT_END_WITH:
                if not isinstance(value, str):
                    raise BadRequestException(
                        f"Value for NOT_END_WITH must be a string, got {type(value).__name__}",
                    )
                return not_(left.endswith(value))

            case QueryOperator.CONTAINS:
                if not isinstance(value, str):
                    raise BadRequestException(
                        f"Value for CONTAINS must be a string, got {type(value).__name__}",
                    )
                return left.contains(value)

            case QueryOperator.NOT_CONTAIN:
                if not isinstance(value, str):
                    raise BadRequestException(
                        f"Value for NOT_CONTAIN must be a string, got {type(value).__name__}",
                    )
                return not_(left.contains(value))

            case _:
                raise BadRequestException(f"Operator {operator} not supported")

    def _filter(self, query: Select, filter_request: FilterRequest) -> Select:
        """Строит запрос, используя типы and/or и операторы equal, in, not_in, not_equal.

        Args:
            query: Исходный запрос.
            filter_request: Фильтры для применения.

        Returns:
            Отфильтрованный запрос.
        """
        for param in filter_request.filters:
            query = self._maybe_join(query, param.field)

        conditions = [  # type: ignore[var-annotated]
            self._get_by(p.field, p.value, p.operator) for p in filter_request.filters
        ]

        if filter_request.type == FilterType.AND:
            return query.where(and_(*conditions))
        else:
            return query.where(or_(*conditions))

    async def _modify_by(
        self,
        field: str,
        value: Any,
        *,
        attributes: dict[str, Any] | None = None,
        operator: QueryOperator = QueryOperator.EQUALS,
        op: Literal["update", "delete"],
        unique: bool = False,
    ) -> ModelType | None | list[ModelType]:
        # 1) Получаем выражение WHERE
        expr = self._get_by(field, value, operator)  # type: ignore[var-annotated]
        conditions = list(expr) if isinstance(expr, tuple) else [expr]

        # 2) Строим stmt
        if op == "update":
            for f, v in (attributes or {}).items():
                self._validate_params(field=f, value=v)
            stmt = (
                update(self.model_class)
                .where(*conditions)
                .values(**(attributes or {}))
                .returning(self.model_class)
            )
        else:  # delete
            stmt = (
                delete(self.model_class).where(*conditions).returning(self.model_class)
            )

        # 3) Оборачиваем
        select_stmt = self._query().from_statement(stmt)

        # 4) Возвращаем
        if unique:
            return await self._one_or_none(select_stmt)
        return await self._all(select_stmt)

    async def _modify_by_filters(
        self,
        filter_request: FilterRequest,
        *,
        attributes: dict[str, Any] | None = None,
        op: Literal["update", "delete"],
        unique: bool = False,
    ) -> ModelType | None | list[ModelType]:
        # 1) Собираем условия
        conditions: list[BinaryExpression] = [
            self._get_by(p.field, p.value, p.operator) for p in filter_request.filters
        ]
        clause = (
            and_(*conditions)
            if filter_request.type == FilterType.AND
            else or_(*conditions)
        )

        # 2) Строим stmt
        if op == "update":
            for f, v in (attributes or {}).items():
                self._validate_params(field=f, value=v)
            stmt = (
                update(self.model_class)
                .where(clause)
                .values(**(attributes or {}))
                .returning(self.model_class)
            )
        else:  # delete
            stmt = delete(self.model_class).where(clause).returning(self.model_class)

        # 3) Оборачиваем в Select…from_statement
        select_stmt = self._query().from_statement(stmt)

        # 4) Возвращаем один или список
        if unique:
            return await self._one_or_none(select_stmt)
        return await self._all(select_stmt)

    def _paginate(self, query: Select, skip: int = 0, limit: int = 100) -> Select:
        """Возвращает запрос, отсортированный по указанной колонке.

        Args:
            query: Запрос для сортировки.
            skip: Количество записей для пропуска.
            limit: Количество записей для возврата.

        Returns:
            Пагинированный запрос.
        """
        if limit > -1:
            query = query.offset(skip).limit(limit)
        return query

    def _sort_by(
        self,
        query: Select,
        sort_by: str | None = None,
        sort_type: SortTypeEnum | None = SortTypeEnum.asc,
    ) -> Select:
        """Возвращает запрос, отсортированный по указанной колонке.

        Args:
            query: Запрос для сортировки.
            sort_by: Поле для сортировки.
            sort_type: Направление сортировки.

        Returns:
            Отсортированный запрос.
        """
        if sort_by is None:
            if hasattr(self.model_class, "updated_at"):
                sort_by = "updated_at"
            else:
                return query

        try:
            order_column = getattr(self.model_class, sort_by)
        except AttributeError as exc:
            raise BadRequestException(
                f"Field {sort_by} not in the fields of the model {self.model_class.__name__}",
            ) from exc

        if sort_type == SortTypeEnum.desc:
            return query.order_by(order_column.desc())

        return query.order_by(order_column.asc())

    async def _all(self, query: Select) -> list[ModelType]:
        """Возвращает все результаты запроса.

        Args:
            query: Запрос для выполнения.

        Returns:
            Список экземпляров модели.
        """
        query = await self.session.scalars(query)
        return query.all()

    async def _one_or_none(self, query: Select) -> ModelType | None:
        """Возвращает первый результат запроса или None."""
        query = await self.session.scalars(query)
        return query.one_or_none()

    async def _count(self, query: Select) -> int:
        """Возвращает количество записей.

        Args:
            query: Запрос для выполнения.

        Returns:
            Количество экземпляров модели.
        """
        query = query.subquery()
        query = await self.session.scalars(select(func.count()).select_from(query))
        return query.one()

    def _get_conflict_fields(self) -> list[str]:
        mapper = inspect(self.model_class)
        table = mapper.local_table
        cols = {col.key for col in table.columns if col.unique}
        for constr in table.constraints:
            if isinstance(constr, UniqueConstraint):
                cols |= {c.key for c in constr.columns}
        return list(cols)

    def __convert_datetime(self, field: str, value: Any) -> datetime | Any:
        if issubclass(self._get_model_field_type(self.model_class, field), datetime):
            try:
                return datetime.fromisoformat(value)
            except ValueError as exc:
                raise FieldException(
                    f"Wrong time format for field {field}. Expected ISO format.",
                ) from exc
            except TypeError as exc:
                raise FieldException(
                    f"Wrong type for field {field}: expected str, received {type(value).__name__}",
                ) from exc
        return value

    def _get_model_field_type(self, _model: ModelType, _field: str) -> type:
        """Получить python-style тип поля."""
        field_type = getattr(_model, _field).type.python_type
        return field_type

    def _resolve_field_relation(self, field: str) -> tuple[ModelType, str]:
        self._check_field_relation_depth(field)
        if "." in field:
            relationship_name, column_name = field.split(".")
            if hasattr(self.model_class, relationship_name):
                model = getattr(
                    self.model_class,
                    relationship_name,
                ).property.mapper.class_
            else:
                raise FieldException(
                    f"{self.model_class.__name__} has no relation with {relationship_name}",
                )
        else:
            model = self.model_class
            column_name = field

        if column_name not in [c.key for c in inspect(model).columns]:
            raise FieldException(f"Wrong field: {field}")

        return model, column_name
