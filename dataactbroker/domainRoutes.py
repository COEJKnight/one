from functools import wraps
from flask import g

from dataactcore.interfaces.db import GlobalDB
from dataactcore.models.domainModels import SubTierAgency
from dataactcore.models.lookups import PERMISSION_SHORT_DICT
from dataactcore.utils.jsonResponse import JsonResponse
from dataactcore.utils.statusCode import StatusCode


DABS_PERMS = [PERMISSION_SHORT_DICT['w'], PERMISSION_SHORT_DICT['s']]
FABS_PERM = PERMISSION_SHORT_DICT['f']


# Add the file submission route
def add_domain_routes(app):
    """ Create routes related to domain values for flask app """

    @app.route("/v1/list_agencies/", methods=["GET"])
    @get_dabs_sub_tier_agencies
    def list_agencies(cgac_sub_tiers, frec_sub_tiers):
        """ List all CGAC and FREC Agencies user has DABS permissions for
            Args:
            cgac_sub_tiers - List of all CGAC SubTierAgencies generated by the get_dabs_sub_tier_agencies decorator,
                required to list only sub_tier_agencies that user has DABS permissions for
            frec_sub_tiers - List of all FREC SubTierAgencies generated by the get_dabs_sub_tier_agencies decorator,
                required to list only sub_tier_agencies that user has DABS permissions for
        """
        cgac_list = [{'agency_name': cst.cgac.agency_name, 'cgac_code': cst.cgac.cgac_code} for cst in cgac_sub_tiers]
        frec_list = [{'agency_name': fst.frec.agency_name, 'frec_code': fst.frec.frec_code} for fst in frec_sub_tiers]

        return JsonResponse.create(StatusCode.OK, {'cgac_agency_list': cgac_list, 'frec_agency_list': frec_list})

    @app.route("/v1/list_all_agencies/", methods=["GET"])
    def list_all_agencies():
        """ List all CGAC and FREC Agencies
        """
        sub_model = SubTierAgency
        sess = GlobalDB.db().session
        agency_list, shared_list = [], []

        # add distinct CGACs from SubTierAgencies with a False is_frec to agency_list
        cgac_sub_tiers = sess.query(sub_model).filter(sub_model.is_frec.is_(False)).distinct(sub_model.cgac_id).all()
        agency_list = [{'agency_name': cst.cgac.agency_name, 'cgac_code': cst.cgac.cgac_code} for cst in cgac_sub_tiers]

        # add distinct FRECs from SubTierAgencies with a True is_frec to shared_list
        frec_sub_tiers = sess.query(sub_model).filter(sub_model.is_frec.is_(True)).distinct(sub_model.frec_id).all()
        shared_list = [{'agency_name': fst.frec.agency_name, 'frec_code': fst.frec.frec_code} for fst in frec_sub_tiers]

        return JsonResponse.create(StatusCode.OK, {'agency_list': agency_list, 'shared_agency_list': shared_list})

    @app.route("/v1/list_sub_tier_agencies/", methods=["GET"])
    @get_fabs_sub_tier_agencies
    def list_sub_tier_agencies(sub_tier_agencies):
        """ List all Sub-Tier Agencies user has FABS permissions for
            Args:
            sub_tier_agencies - List of all SubTierAgencies generated by the get_fabs_sub_tier_agencies decorator,
                required to list only sub_tier_agencies that user has FABS permissions for
        """
        agencies = []
        for sub_tier in sub_tier_agencies:
            agency_name = sub_tier.frec.agency_name if sub_tier.is_frec else sub_tier.cgac.agency_name
            agencies.append({'agency_name': '{}: {}'.format(agency_name, sub_tier.sub_tier_agency_name),
                             'agency_code': sub_tier.sub_tier_agency_code, 'priority': sub_tier.priority})

        return JsonResponse.create(StatusCode.OK, {'sub_tier_agency_list': agencies})


def get_dabs_sub_tier_agencies(fn):
    """ Decorator which provides a list of all SubTierAgencies the user has DABS permissions for. The function should
    have a cgac_sub_tiers and a frec_sub_tiers parameter as its first argument. """
    @wraps(fn)
    def wrapped(*args, **kwargs):
        cgac_sub_tiers, frec_sub_tiers = [], []
        if g.user is not None:
            # create list of affiliations
            cgac_ids, frec_ids = separate_affiliations(g.user.affiliations, 'dabs')

            # generate SubTierAgencies based on DABS permissions
            all_cgac_sub_tiers, all_frec_sub_tiers = get_sub_tiers_from_perms(g.user.website_admin, cgac_ids, frec_ids)

            # filter out copies of top-tier agencies
            cgac_sub_tiers = all_cgac_sub_tiers.distinct(SubTierAgency.cgac_id).all()
            frec_sub_tiers = all_frec_sub_tiers.distinct(SubTierAgency.frec_id).all()

        return fn(cgac_sub_tiers, frec_sub_tiers, *args, **kwargs)
    return wrapped


def get_fabs_sub_tier_agencies(fn):
    """ Decorator which provides a list of all SubTierAgencies the user has FABS permissions for. The function should
    have a sub_tier_agencies parameter as its first argument. """
    @wraps(fn)
    def wrapped(*args, **kwargs):
        sub_tier_agencies = []
        if g.user is not None:
            # create list of affiliations
            cgac_ids, frec_ids = separate_affiliations(g.user.affiliations, 'fabs')

            # generate SubTierAgencies based on FABS permissions
            all_cgac_sub_tiers, all_frec_sub_tiers = get_sub_tiers_from_perms(g.user.website_admin, cgac_ids, frec_ids)

            sub_tier_agencies = all_cgac_sub_tiers.all() + all_frec_sub_tiers.all()

        return fn(sub_tier_agencies, *args, **kwargs)
    return wrapped


def get_sub_tiers_from_perms(is_admin, cgac_affil_ids, frec_affil_ids):
    sess = GlobalDB.db().session
    cgac_sub_tier_agencies = sess.query(SubTierAgency).filter(SubTierAgency.is_frec.is_(False))
    frec_sub_tier_agencies = sess.query(SubTierAgency).filter(SubTierAgency.is_frec.is_(True))

    # filter by user affiliations if user is not admin
    if not is_admin:
        cgac_sub_tier_agencies = cgac_sub_tier_agencies.filter(SubTierAgency.cgac_id.in_(cgac_affil_ids))
        frec_sub_tier_agencies = frec_sub_tier_agencies.filter(SubTierAgency.frec_id.in_(frec_affil_ids))

    return cgac_sub_tier_agencies, frec_sub_tier_agencies


def separate_affiliations(affiliations, app_type):
    cgac_ids, frec_ids = [], []

    for affil in g.user.affiliations:
        perm_type = affil.permission_type_id
        if (app_type == 'fabs' and perm_type == FABS_PERM) or (app_type == 'dabs' and perm_type in DABS_PERMS):
            if affil.frec:
                frec_ids.append(affil.frec.frec_id)
            else:
                cgac_ids.append(affil.cgac.cgac_id)

    return cgac_ids, frec_ids
