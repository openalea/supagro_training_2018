""" A collection of simple allometric functions for parameterising the
architecture of maize"""
import numpy
import pandas

from itertools import cycle
from scipy.interpolate import interp1d

from plant_design import get_form_factor, blade_length,blade_dimension,\
    stem_dimension, load_leaf_db, get_base_width, truncate_leaf

from fitting import fit3

def maize_leaves_path():
    import os
    import openalea.cereals
    data_dir = os.path.dirname(openalea.cereals.__file__)
    return os.path.join(data_dir, 'leaves_simple.db')


def bell_shaped_dist(plant_area=1, nb_phy=15, rmax=.7, skew=0.15):
    """ returns leaf area of individual leaves along bell shaped model """

    k = -numpy.log(skew) * rmax
    r = numpy.linspace(1. / nb_phy, 1, nb_phy)
    relative_surface = numpy.exp(
        -k / rmax * (2 * (r - rmax) ** 2 + (r - rmax) ** 3))
    leaf_area = relative_surface / relative_surface.sum() * plant_area
    return leaf_area.tolist()


def geometric_dist(height=15, nb_phy=15, q=1):
    """ returns distances between individual leaves along a geometric model """

    if q == 1:
        u0 = float(height) / nb_phy
    else:
        u0 = height * (1. - q) / (1. - q ** (nb_phy + 1))

    return [u0 * q ** i for i in range(nb_phy)]


def leaf_azimuth(size=1, phyllotactic_angle=180, phyllotactic_deviation=15, plant_orientation=0, spiral=True):
    """ Generate leaf azimuth series

    Args:
        size: the size of the sample
        phyllotactic_angle: if spiral=False (default) the phyllotactic angle (deg) bet
        ween 'left and right' leaves. If spiral is True, the angle between
        successive leaves (deg)
        phyllotactic_deviation: half-amplitude of deviation around phyllotactic
        angle (deg)
        plant_orientation : first azimuth of the serie (deg, from X+ positive
        counter-clockwise)

    Returns:
        an array of azimuths (deg, from X+, positive counter-clockwise)
    """
    if size == 1:
        return plant_orientation
    if spiral:
        main = numpy.arange(0, size) * phyllotactic_angle
    else:
        it = cycle((0, phyllotactic_angle))
        main = numpy.array([it.next() for i in xrange(size)])
    azim = plant_orientation + main + (numpy.random.random(size) - 0.5) * 2 * phyllotactic_deviation
    azim = azim % 360
    return numpy.where(azim <= 180, azim, azim - 360)


# def leaf_shape_perez(nb_segment=100, insertion_angle=50, delta_angle=180, coef_curv=-0.2):
#     def _curvature(s, coef_curv):
#         return ((1 + coef_curv) * (s**2)) / (1 + coef_curv * (s**2))
#         # positionRelativeLeaf=vector of relative position on the leaf [0;1]
#         # decli_ini = declination (=inclination from the vertical) at leaf insertion (degree) [0;180]
#         # decli_final = declination (=inclination from the vertical) at leaf tip (degree) [decli_ini; 180]
#         # coefCurv= coefficient of leaf curvature [-1,inf] -1=no curvature inf=curvature at insertion
#         # leafLength = length of the leaf
#
#     s = numpy.linspace(0,1,nb_segment+1)
#     ds = 1. / (nb_segment)
#     angle_simu = _curvature(s, coef_curv=coef_curv) * numpy.radians(
#         delta_angle) + numpy.radians(insertion_angle)
#     dx = numpy.array([0] + (ds * numpy.sin(angle_simu)).tolist())[:-1]
#     dy = numpy.array([0] + (ds * numpy.cos(angle_simu)).tolist())[:-1]
#     x, y = numpy.cumsum(dx), numpy.cumsum(dy)
#     length = numpy.sum(numpy.sqrt(dx**2 + dy**2))
#     return x / length, y / length

def leaf_shape_perez(nb_segment = 100,insertion_angle=50, l=0.5, infl=30):
    # insertion_angle:  leaf insertion angle from the vertical (degree)
    # l:  relative position on the midrib of the transition bteween the 2 sections of the curve
    # infl : inflexion point (in degree) related to difference between insertion angle and final angle (delta angle)

    def _sigmo(x,max,slope,infl):
        return(max / (1+numpy.exp(4*slope*(infl-x))))

    def _curvature(s, coef_curv):
        return ((1 + coef_curv) * (s**2)) / (1 + coef_curv * (s**2))

    #inputs

    s = numpy.linspace(0,1,nb_segment+1)
    ds = 1. / (nb_segment)
    # fraction of delta angle reach at l
    frac_l = 2. / 3
    # curvature coefficient of the first section (before l)
    coefCurv_1 = -0.2
    # curvature coefficient of the second section (after l)
    coefCurv_2 = 5

    #leaf tip angle
    tip_angle = numpy.maximum(insertion_angle, _sigmo(x=insertion_angle, max=240, slope=0.02, infl=infl))

    # leaf angle at l
    l_angle = insertion_angle + frac_l*(tip_angle - insertion_angle)

    #angles in the first section of the curve
    angle_simu_1 = _curvature(s, coef_curv=coefCurv_1) * numpy.radians(l_angle-insertion_angle) + numpy.radians(insertion_angle)

    # angles in the second section of the curve
    angle_simu_2 = _curvature(s[1:], coef_curv=coefCurv_2) * numpy.radians(tip_angle - l_angle) + numpy.radians(l_angle)

    #all angles
    angle_simu=numpy.array(angle_simu_1.tolist()+angle_simu_2.tolist())
    coef_l=[l]*len(s)+[1-l]*len(s[1:])

    dx = numpy.array([0] + (coef_l * numpy.sin(angle_simu)).tolist())[:-1]
    dy = numpy.array([0] + (coef_l * numpy.cos(angle_simu)).tolist())[:-1]
    x, y = numpy.cumsum(dx), numpy.cumsum(dy)
    length = numpy.sum(numpy.sqrt(dx**2 + dy**2))
    return x / length, y / length


def sr_prevot(nb_segment=10, alpha=-2.5):
    beta = -2 * (alpha + numpy.sqrt(-alpha))
    gamma = 2 * numpy.sqrt(-alpha) + alpha
    s = numpy.linspace(0, 1, nb_segment + 1)
    r = alpha * s**2 + beta * s + gamma
    return s, r

def leaf_morpho_rel(nb_segment=10, w0=0.5, lm=0.5):
    a0 = w0
    c0 = (w0 - 1) / (lm ** 2)
    b0 = -2 * c0 * lm

    c1 = -1 / (1 - lm) ** 2
    b1 = -2 * c1 * lm
    a1 = -b1 - c1

    s = numpy.linspace(0, 1, nb_segment + 1)

    r1 = numpy.array(a0+b0*s[s <=lm]+c0*s[s <=lm]**2)
    r2 = numpy.array(a1+b1*s[s >lm]+c1*s[s >lm]**2)
    r = numpy.concatenate([r1,r2])
    return s, r

# def leaf_area_rel(r,w0,lm):
#     a0 = w0
#     c0 = (w0 - 1) / (lm ** 2)
#     b0 = -2 * c0 * lm
#
#     c1 = -1 / (1 - lm) ** 2
#     b1 = -2 * c1 * lm
#     a1 = -b1 - c1
#
#     if (r<=lm): s = (a0 * r + b0 / 2 * r ** 2 + c0 / 3 * r ** 3)
#     if (r > lm):s= a0 * lm + b0 / 2 * lm ** 2 + c0 / 3 * lm ** 3 + (a1 * r + b1 / 2 * r ** 2 + c1 / 3 * r ** 3) - (a1 * lm + b1 / 2 * lm ** 2 + c1 / 3 * lm ** 3)
#
#     return s, r


# def parametric_leaf(nb_segment=10, insertion_angle=50, pos_l=0.5,
#                     infl=30, alpha=-2.5):
def parametric_leaf(nb_segment=10, insertion_angle=50, pos_l=0.5,
                    infl=30, w0=0.5, lm=0.5):
    """

    Args:
        nb_segment:
        insertion_angle:
        delta_angle:
        coef_curv:
        alpha:

    Returns:

    """
    nseg = min(100, nb_segment)
    # x, y = leaf_shape_perez(nseg, insertion_angle, delta_angle, coef_curv)
    x, y = leaf_shape_perez(nseg, insertion_angle, pos_l, infl)
    # s, r = sr_prevot(nseg, alpha)
    s, r = leaf_morpho_rel(nb_segment=nseg, w0=w0, lm=lm)
    return fit3(x, y, s, r, nb_points=nb_segment)

def interpolate_at_stage(mature_plant, stage=None):
    """Compute sate of a maize plant at a given stage from mature plant
    information

    Args:
        mature_plant: a pandas dataframe decribing the plant at a given stage
        stage: decimal leaf stage (number of ligulated leaves).

    Returns:a pandas dataframe with visibility and updated leaf length

    """
    # stage is collar-based scale
    if stage is None:
        return mature_plant
    # Lb_vis = partie visible (enroulee + deroulee)
    # Lb_rolled = partie visible enroulee
    # W_rolled = stem diameter at the top of the rolled element
    df = mature_plant.copy(deep=True)
    phytomer = df.leaf_rank.max()
    # Lejeune an Bernier tips at floral transiion
    floral_transition = (phytomer - 1.95) / 1.84
    # collars at floral transition
    collar_at_transition = float(floral_transition) / 1.8
    # emerging leaf at transition will be the first on type II
    first_type2 = int(round((phytomer - 1.95) / 1.84)) + 1
    # last pure vegetative is the one whose collars is emmerged
    last_type1 = int(collar_at_transition)


    # dls decimal leaf stage: up to collar app = nb tip at floral transition
    # dls = collars * 1.8,
    # afterwards
    # dls = 1.8 * (0.7 * (collars - floral_transition) +  floral_transition)
    dls = stage * 1.8
    if stage > floral_transition:
        dls = 1.8 * (floral_transition + 0.7 * (stage - floral_transition))

    # phyllo = 1
    TTtip = df['leaf_rank']
    TTtrans = 1.8 * floral_transition
    TTdeb = 0.85 * TTtip
    TTcol1 = 1.8 * TTtip
    TTcol2 = TTtrans + 0.7 * (TTcol1 - TTtrans)
    TTcol = numpy.where(TTcol1 <= TTtrans, TTcol1, TTcol2)
    # TODO: add small delay between collar and end
    TTend1 = 1.8 * TTtip + 0.2
    TTend2 = TTtrans + 2 + 0.7 * (TTcol1 - TTtrans)
    TTend = numpy.where(TTend1 <= TTtrans + 0.2, TTend1,TTend2)

    frac = (dls - TTtip) / (TTcol - TTtip)
    Lb_vis = df['L_blade'] * numpy.maximum(numpy.minimum(frac, 1), 0)
    frac = (dls - TTcol) / (TTend - TTcol)
    Le_vis = df['L_internode'] * numpy.maximum(numpy.minimum(frac, 1), 0)
    # full metamer growth
    frac = (dls - TTdeb) / (TTend - TTdeb)
    lphy = (df['L_blade'] + df['L_internode']) * numpy.maximum(numpy.minimum(frac, 1), 0)
    lhide = lphy - Lb_vis - Le_vis
    # ppour les ligules on enroule pas
    # au dessus on initialise hw = lhide derniere ligulee
    # a chaque phyto si lhide - hw > 0, on enroule le limbe n-1 et hw devient lhide
    # => lroll = 0 si lig, et lroll n-1 = diff(lhide) n si positif !
    collars = int(min(stage, phytomer - 1))
    lroll = [0] * collars + numpy.diff(lhide[collars:]).tolist() + [0]
    Lb_rolled = numpy.maximum(0, lroll)
    fvis = (Lb_vis - Lb_rolled) / df['L_blade']
    W_rolled = [get_base_width(leaf, fv) * wmax for leaf, fv, wmax in zip(df['leaf_shape'], fvis, df['W_blade'])]

    df['L_blade'] = Lb_vis - Lb_rolled
    df['leaf_shape'] = [truncate_leaf(leaf, frac) for leaf, frac in zip(df['leaf_shape'], fvis)]
    df['L_internode'] = Le_vis + Lb_rolled
    df['h_ins'] = df['L_internode'].cumsum()
    # top diameter
    df['W_sheath'] = numpy.where(df['leaf_rank'] <= stage, df['W_internode'], numpy.array(W_rolled)/ numpy.pi )

    return df

# def simple_maize(plant_area=10000, plant_height=200, pseudostem_height=20,
#                  phytomer=16, rmax=0.67, pseudostem_dist=1.4, stem_dist=1.,
#                  diam_base=2.5, diam_top=1, leaves=None, phyllotactic_angle=180,
#                  phyllotactic_deviation=15, plant_orientation=0, wl=0.1, skew=0.15, seed=None,stage=None):

def simple_maize(plant_area=10000,
                      plant_height=200,
                      pseudostem_height=20,
                      phytomer=16,
                      rmax=0.67,
                      pseudostem_dist=1.4,
                      stem_dist=1.,
                      diam_base=2.5,
                      diam_top=1,
                      leaves=None,
                      phyllotactic_angle=180,
                      phyllotactic_deviation=15,
                      plant_orientation=0,
                      skew=0.15,
                      wl_int=0.08,
                      wl_slp=0.003 ,
                      w0_int=0.5,
                      w0_slp=0.01,
                      lm_int=0.5,
                      lm_slp=-0.02,
                      seed=None,
                      stage=None):
    """ Generate a detailed parameter set for maize simulation from global
    parameters

    Args:
        plant_area: the total leafy area of the plant
        plant_height:  height of the stem
        pseudostem_height:  height of the highestpseudo-stem collar
        phytomer: number of phytomers
        leaf rank function
        rmax: control the magitude of the leaf area as a function of
        leaf rank function
        pseudostem_dist: parameter contrling spacing between pseudostem leaves
        stem_dist: parameter controling spacing between stem leaves
        diam_base: diameter at the base of the stem
        diam_top: dimaeter at the top of the stem
        leaves: a {rank: (x, y, s, r)} dict of tuples defining the (x,y)
        coordinates of leaf midribs and (s,r) coordinate defining the radius as
        a function of distance to leaf base
        phyllotactic_angle: phyllotactic angle between successive leaves (deg)
        phyllotactic_deviation: absolute deviation around phyllotactic angle (deg)
        plant_orientation: azimuth orientation (deg, from X+, positive
        counter-clockwise) of the first leaf of the plant

    Returns: A pandas Dataframe with individual organ dimensions and geometric
    parameters needed by cereals constructors

    """

    numpy.random.seed(seed)
    ranks = range(1, phytomer + 1)
    ntop = max(ranks) - numpy.array(ranks) + 1
    if leaves is None:
        path = maize_leaves_path()
        db = load_leaf_db(path)
        leaves = {rank: db.get(str(rank), db['10'])[0] for rank in ranks}

    phytomer = int(phytomer)

    # Lejeune an Bernier formula + col =
    nb_young_phy = int(round((phytomer - 1.95) / 1.84 / 1.3))

    # compute the leaf surface
    leaf_area = numpy.array(
        bell_shaped_dist(plant_area=plant_area, nb_phy=phytomer, rmax=rmax,
                         skew=skew))

    # distances between leaves
    pseudostem = geometric_dist(pseudostem_height, nb_young_phy,
                                pseudostem_dist)
    stem = geometric_dist(plant_height - pseudostem_height,
                          phytomer - nb_young_phy, stem_dist)
    internode = pseudostem + stem

    # stem diameters
    diameter = ([diam_base] * nb_young_phy +
                numpy.linspace(diam_base, diam_top,
                               phytomer - nb_young_phy).tolist())

    ff = [get_form_factor(leaves[rank]) for rank in ranks]


    length = blade_length(area=leaf_area, ntop=ntop, wl_int=wl_int, wl_slp=wl_slp,w0_int=w0_int,w0_slp=w0_slp,lm_int=lm_int,lm_slp=lm_slp)
    blades = blade_dimension(area=leaf_area, form_factor=ff, ntop=ntop, length=length)
    stem = stem_dimension(internode=internode, d_internode=diameter, ntop=ntop)
    df = blades.merge(stem)

    df['leaf_azimuth'] = leaf_azimuth(size=len(ranks), phyllotactic_angle=phyllotactic_angle, phyllotactic_deviation=phyllotactic_deviation,
                                      plant_orientation=plant_orientation)
    df['leaf_rank'] = ranks
    df['leaf_shape'] = [leaves[n] for n in df.leaf_rank]

    df = interpolate_at_stage(df, stage)

    return df


