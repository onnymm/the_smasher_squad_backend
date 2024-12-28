from datetime import datetime
from enum import Enum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import (
    Integer,
    DateTime,
    Integer,
    String,
    Boolean,
    Enum as SQLEnum
)

# Base para las tablas de la base de datos
class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(Integer, primary_key= True, autoincrement= True)
    create_date: Mapped[DateTime] = mapped_column(DateTime, default= datetime.now)
    write_date: Mapped[DateTime] = mapped_column(DateTime, default= datetime.now, onupdate= datetime.now)

# Comportamiento genérico para clases enum
class db_enum(Enum):
    def __str__(self):
        return self.value

# ENUM de colores de sistemas solares
class SolarSystemColor(db_enum):
    white = "white"
    red = "red"
    green = "green"
    blue = "blue"
    purple = "purple"
    yellow = "yellow"

# ENUM de roles de la alianza
class AllianceRole(db_enum):
    private = "private"
    captain = "captain"
    general = "general"


# Usuarios
class Users(Base):

    __tablename__ = "users"
    user: Mapped[str] = mapped_column(String(24), nullable= False, unique= True)
    name: Mapped[str] = mapped_column(String(60), nullable= False)
    avatar: Mapped[str] = mapped_column(String(100), nullable= True)
    password: Mapped[str] = mapped_column(String(60), nullable= False)


# Alianzas
class Alliances(Base):

    __tablename__ = "alliances"

    name: Mapped[str] = mapped_column(String(25), nullable= False)
    logo: Mapped[str] = mapped_column(String(20), nullable= False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)

    enemies: Mapped[list["Enemies"]] = relationship("Enemies", back_populates="alliance")
    war: Mapped[list["CurrentWar"]] = relationship("CurrentWar", back_populates="alliance")
    coords: Mapped[list["Coordinates"]] = relationship("Coordinates", back_populates="alliance")


# Enemigos
class Enemies(Base):

    __tablename__ = "enemies"

    name: Mapped[str] = mapped_column(String(25), nullable=False)
    avatar: Mapped[str] = mapped_column(String(100), nullable= True)
    level: Mapped[int] = mapped_column(Integer, nullable= False)
    role: Mapped[AllianceRole] = mapped_column(SQLEnum(AllianceRole))
    alliance_id: Mapped[int] = mapped_column(ForeignKey("alliances.id"), nullable= True)
    alliance: Mapped["Alliances"] = relationship("Alliances", back_populates= "enemies")
    coords: Mapped[list["Coordinates"]] = relationship("Coordinates", back_populates="enemy")


# Coordenadas
class Coordinates(Base):

    __tablename__ = "coords"

    x: Mapped[int] = mapped_column(Integer, nullable= True)
    y: Mapped[int] = mapped_column(Integer, nullable= True)
    war: Mapped[bool] = mapped_column(Boolean, nullable= False)
    planet: Mapped[int] = mapped_column(Integer)
    color: Mapped[SolarSystemColor] = mapped_column(SQLEnum(SolarSystemColor), nullable= True)
    starbase_level: Mapped[int] = mapped_column(Integer)
    under_attack_since: Mapped[DateTime] = mapped_column(DateTime, nullable= True)
    attacked_at: Mapped[DateTime] = mapped_column(DateTime, nullable= True)

    enemy_id: Mapped[int] = mapped_column(ForeignKey("enemies.id"))
    enemy: Mapped["Enemies"] = relationship("Enemies", back_populates= "coords")

    create_uid: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable= False)
    write_uid: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable= False)
    creator: Mapped["Users"] = relationship("Users", foreign_keys=[create_uid])
    updater: Mapped["Users"] = relationship("Users", foreign_keys=[write_uid])

    alliance_id: Mapped[int] = mapped_column(ForeignKey("alliances.id"), nullable= True)
    alliance: Mapped["Alliances"] = relationship("Alliances", back_populates= "coords")


# Guerra actual
class CurrentWar(Base):

    __tablename__ = "war"

    alliance_id: Mapped[int] = mapped_column(ForeignKey("alliances.id"), nullable= True)
    alliance: Mapped["Alliances"] = relationship("Alliances", back_populates= "war")
    regeneration_hours: Mapped[int] = mapped_column(Integer, nullable= True)
