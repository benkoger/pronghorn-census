# Multi table bindings for the projectmanagement schema
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass
from typing import ClassVar

import psycopg.sql as sql

from ..base import Relationbase

# ---------------------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectsHerdUnits(Relationbase):
    project_id: int
    herd_unit_id: int

    __table__: ClassVar[sql.Identifier] = sql.Identifier("projectmanagement", "projects_herd_units")
    __key__: tuple = ("project_id", "herd_unit_id")


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectsModels(Relationbase):
    project_id: int
    model_id: int

    __table__: ClassVar[sql.Identifier] = sql.Identifier("projectmanagement", "projects_models")
    __key__: tuple = ("project_id", "model_id")


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectsSurveys(Relationbase):
    project_id: int
    survey_id: int

    __table__: ClassVar[sql.Identifier] = sql.Identifier("projectmanagement", "projects_surveys")
    __key__: tuple = ("project_id", "survey_id")


# --------------------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectsSchemas(Relationbase):
    project_id: int
    survey_id: int

    __table__: ClassVar[sql.Identifier] = sql.Identifier("projectmanagement", "projects_schemas")
    __key__: tuple = ("project_id", "schema_id")


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SurveysHerdUnits(Relationbase):
    survey_id: int
    herd_unit_id: int

    __table__: ClassVar[sql.Identifier] = sql.Identifier("projectmanagement", "surveys_herd_units")
    __key__: tuple = ("survey_id", "herd_unit_id")
