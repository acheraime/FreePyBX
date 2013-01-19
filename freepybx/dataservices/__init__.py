"""The application's model objects"""
from freepybx.model.meta import db, Base, User, Customer, Shift, EmailAccount, PbxAccount, PbxDid, PbxProfile, PbxGateway, \
    PbxRoute, PbxEndpoint, PbxCondition, PbxGroup, PbxGroupMember, PbxAction, PbxCdr


def init_model(engine):
    """Call me before using any of the tables or classes in the model"""
    db.configure(bind=engine)

    """Call me before using any of the tables or classes in the model"""
    db.configure(bind=engine, expire_on_commit=False )
    Base.query = db.query_property()
    metadata = Base.metadata


Base.query = db.query_property()
metadata = Base.metadata