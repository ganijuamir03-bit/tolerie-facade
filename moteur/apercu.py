"""Aperçus PNG pour l'interface : flan DXF (2D) et pièce STEP (3D)."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def apercu_dxf(chemin_dxf: str, chemin_png: str) -> str:
    import ezdxf
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    doc = ezdxf.readfile(chemin_dxf)
    msp = doc.modelspace()
    fig = plt.figure(figsize=(14, 4))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
    Frontend(RenderContext(doc), MatplotlibBackend(ax)).draw_layout(msp, finalize=True)
    fig.savefig(chemin_png, dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return chemin_png


def apercu_step(chemin_step: str, chemin_png: str, titre: str = "") -> str:
    from build123d import import_step
    import numpy as np
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    part = import_step(chemin_step)
    verts, tris = part.tessellate(0.5)
    V = np.array([(v.X, v.Y, v.Z) for v in verts]); F = np.array(tris)
    fig = plt.figure(figsize=(9, 5)); ax = fig.add_subplot(111, projection="3d")
    ax.add_collection3d(Poly3DCollection(V[F], facecolor="#9db4c0",
                                         edgecolor="#33475b", linewidths=0.2))
    mins, maxs = V.min(0), V.max(0); ctr = (mins + maxs) / 2; span = (maxs - mins).max() / 2
    ax.set_xlim(ctr[0]-span, ctr[0]+span); ax.set_ylim(ctr[1]-span, ctr[1]+span)
    ax.set_zlim(ctr[2]-span, ctr[2]+span)
    ax.view_init(elev=22, azim=-58); ax.set_box_aspect((1, 1, 1))
    ax.set_axis_off()
    if titre:
        ax.set_title(titre)
    fig.savefig(chemin_png, dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return chemin_png
