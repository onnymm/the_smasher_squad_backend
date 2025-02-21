from pydantic import BaseModel, Field
from dml_manager import CriteriaStructure

class BaseDataRequest(BaseModel):
    """
    ## Estructura para solicitud de vista de datos
    - `page` `int`: Número de página.
    - `items_per_page` `int`: Número de registros por página.
    - `sortby` `str | list[str] | None`: Ordenar por.
    - `ascending` `bool | list[bool]`: Orden ascendente.
    - `search_criteria` `CriteriaStructure`: Criterio de búsqueda.
    """
    search_criteria: CriteriaStructure = []
    fields: list[str] = []
    page: int = Field(
        ge= 0,
        description= 'Página del conjunto de registros a mostrar. Esto va en función del número de registros por página (`items_per_page`).'
    )
    items_per_page: int = Field(
        default= 40,
        ge= 0,
        description= 'Número de registros a mostrar por página.'
    )
    sortby: str | list[str] | None = Field(
        default= None,
        description= 'Ordenar por algún campo de los registros.'
    )
    ascending: bool | list[bool] = Field(
        default= True,
        description= 'Ordenamiento ascendente o descendente, en función del campo a usar para ordenar en el parámetro `sortby`.'
    )
