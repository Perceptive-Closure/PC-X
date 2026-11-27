"""Regenerate the five vector figures beside this file with Python and Matplotlib."""
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from matplotlib.ticker import PercentFormatter

OUT = Path(__file__).resolve().parent
DATE = datetime(2026, 11, 27, tzinfo=timezone.utc)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "pdf.fonttype": 42,
                     "axes.unicode_minus": False, "text.color": "#152f3c"})
NAVY, TEAL, RUST, GRAY = "#173747", "#14675e", "#9b462b", "#58707c"
PALE, SAND, LINE = "#e7f2ee", "#f8ece5", "#aab9bc"


def canvas(width, height):
    fig, ax = plt.subplots(figsize=(width, height))
    fig.subplots_adjust(0, 0, 1, 1)
    ax.set(xlim=(0, width), ylim=(0, height), aspect="equal")
    ax.axis("off")
    return fig, ax


def save(fig, name):
    fig.savefig(OUT / (name + ".pdf"), metadata={"Creator": "PC-X manuscript",
                "CreationDate": DATE, "ModDate": DATE})
    plt.close(fig)


def box(ax, x, y, w, h, title, description="", color=PALE):
    ax.add_patch(FancyBboxPatch((x,y), w,h, boxstyle="round,pad=0.015,rounding_size=0.04",
                                facecolor=color, edgecolor=LINE, linewidth=.65))
    ax.text(x+.105,y+h*(.67 if description else .5),title,ha="left",va="center",
            fontweight="bold",color=NAVY,fontsize=8.5)
    if description:
        ax.text(x+.105,y+.18*h,description,ha="left",va="bottom",fontsize=7.5,color=NAVY)


def arrow(ax, p, q):
    ax.add_patch(FancyArrowPatch(p,q,arrowstyle="-|>",mutation_scale=10,color=GRAY,
                                lw=.9,shrinkA=2,shrinkB=2))


def worlds():
    fig, ax = canvas(7.3, 2.15)
    ax.text(.12,1.92,"Compatible after rehearsal",fontweight="bold",color=NAVY)
    ax.text(4.88,1.92,"After the guard read",fontweight="bold",color=NAVY)
    for i,(backend,good) in enumerate([("Compiler A",True),("Compiler B",True),
                                        ("Compiler A",False),("Compiler B",False)]):
        y=1.45-i*.40
        ax.text(.13,y,backend,va="center",fontsize=8)
        ax.text(1.17,y,"All routes guarded" if good else "Legacy route admitted",va="center",
                color=TEAL if good else RUST,fontsize=8)
        if good:
            box(ax,4.87,y-.15,2.21,.30,backend+"  ·  guarded")
    arrow(ax,(3.02,1.24),(4.70,1.24))
    ax.text(3.83,.99,"Installed route\nand guard checked",ha="center",va="top",fontsize=7.6)
    ax.text(4.87,.33,"One target value;\ntwo installations.",fontsize=8,color=TEAL)
    save(fig,"worlds")


def pillars():
    fig, ax = canvas(7.3, 2.25)
    items=[("Identification","Which values survive?"),("Acquisition","Which read separates them?"),
           ("Generalization","Does the bound transfer?"),("Strategic oversight","What can a responder hide?"),
           ("Verification","Is the measured event real?"),("Realization","What work can proceed?")]
    positions=[(.07,1.29),(2.54,1.29),(5.01,1.29),(.07,.22),(2.54,.22),(5.01,.22)]
    for i,((title,desc),(x,y)) in enumerate(zip(items,positions)):
        box(ax,x,y,2.21,.73,title,desc,PALE if i%2==0 else "#edf1f3")
    for i in (0,1,3,4):
        x,y=positions[i]
        arrow(ax,(x+2.20,y+.36),(x+2.46,y+.36))
    ax.plot([6.11,6.11,1.18],[1.28,1.09,1.09],color=GRAY,lw=.8)
    arrow(ax,(1.18,1.10),(1.18,.95))
    save(fig,"pillars")


def transport():
    fig, ax=canvas(7.1,1.98)
    left, width=1.76,4.67
    for y, title in [(1.22,"Evaluation"),(.56,"Deployment")]:
        ax.text(.12,y+.18,title,fontweight="bold",va="center")
        ax.add_patch(Rectangle((left,y),.90*width,.34,facecolor=PALE,edgecolor=TEAL,lw=.8))
        ax.add_patch(Rectangle((left+.90*width,y),.1*width,.34,facecolor=SAND,edgecolor=RUST,lw=.8,hatch="//"))
        ax.text(left+.45*width,y+.17,"at least 90% paired on the declared event",
                fontsize=8,ha="center",va="center",color=TEAL)
    ax.text(left+.9*width,.24,"unmatched",color=RUST,fontsize=7.5,ha="center")
    ax.text(.12,.04,"Illustrative masses. A binary risk can differ by at most 0.10 under this match.",
            fontsize=8,color=GRAY)
    save(fig,"transport")


def service():
    fig, ax=canvas(7.4,2.76)
    box(ax,.1,1.81,1.99,.68,"Guard revision","One setup check")
    box(ax,2.47,1.81,2.01,.68,"Prelude and intake","Work + route receipt")
    box(ax,4.91,1.81,2.30,.68,"Choose observation","Low, high or skip")
    box(ax,4.91,.59,2.30,.68,"Binary verdict","Issue or stop")
    box(ax,2.47,.59,2.01,.68,"On issuance","Carried proposal")
    box(ax,.10,.59,1.99,.68,"Finalizer","Fresh physical draw")
    for p,q in [((2.1,2.15),(2.45,2.15)),((4.48,2.15),(4.9,2.15)),((6.06,1.8),(6.06,1.28)),
                ((4.91,.93),(4.49,.93)),((2.47,.93),(2.1,.93))]:
        arrow(ax,p,q)
    ax.text(.12,.18,"Independent scoring reads actual violation, issuance and completed jobs.",
            fontsize=8,color=GRAY)
    save(fig,"service")


def risk():
    # Issued-set estimates and simultaneous bounds (%) as printed in EXP-X17/RESULTS.md
    # at revision 899f29dbdcc6e9a81a32bbaf387c3bf270501b10, in roster order.
    primary=[(9.29,4.93,13.65),(19.57,13.44,25.70),(8.50,4.45,12.56),(26.45,19.39,33.51),
             (9.94,5.80,14.07),(9.80,5.52,14.07),(24.31,17.97,30.65),(25.47,18.73,32.20)]
    independent=[(9.41,5.12,13.71),(23.21,17.13,29.30),(8.82,4.77,12.87),(28.47,21.48,35.47),
                 (10.02,5.89,14.14),(8.82,4.53,13.10),(25.00,18.65,31.35),(24.46,17.69,31.23)]
    fig, ax=plt.subplots(figsize=(7.1,3.38))
    fig.subplots_adjust(left=.10,right=.975,top=.82,bottom=.16)
    for data,offset,color,marker,title in [(primary,-.16,TEAL,"o","Primary"),
                                           (independent,.16,NAVY,"s","Independent")]:
        estimates=[a for a,_,_ in data]
        ax.errorbar(estimates,[i+offset for i in range(8)],
                    xerr=[[a-b for a,b,_ in data],[c-a for a,_,c in data]],fmt=marker,
                    markersize=3.6,capsize=2,color=color,linewidth=1,label=title)
    ax.axvline(37.5,color=RUST,linestyle="--",label="Declared cap (3/8)",lw=1.3)
    ax.set(yticks=range(8),yticklabels=[f"s{i:02d}" for i in range(1,9)],xlim=(0,40),
           xticks=[0,10,20,30,40],xlabel="Violations among issued runs")
    ax.xaxis.set_major_formatter(PercentFormatter(100,0))
    ax.invert_yaxis()
    ax.set_axisbelow(True)
    ax.grid(axis="x",linewidth=.5,color="#d7dddf")
    ax.legend(loc="lower left",bbox_to_anchor=(0,1.025),ncol=3,frameon=False,fontsize=8)
    for side in ("right","top","left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(LINE)
    ax.tick_params(length=0,pad=4)
    save(fig,"risk")


if __name__ == "__main__":
    for figure in (worlds, pillars, transport, service, risk):
        figure()
