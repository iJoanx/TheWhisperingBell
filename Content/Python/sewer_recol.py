"""Recomputes the collision of every crossing / junction / shaft in the OPEN level (no rebuild).
    py sewer_recol.py        -> log in Content/Python/collision_out.txt"""
import importlib
import sewer_builder, sewer_boxcol
importlib.reload(sewer_builder)
importlib.reload(sewer_boxcol)
sewer_builder.use_definitive()
sewer_boxcol.apply_level()
