import copy
import json
import os
from unittest.mock import patch
import pytest

P={'source':'human','by':'fixture','state':'USER_LOCKED'}

def profile():
    return {'schema_version':2,'revision':9,'approved':True,'face':{'text_en':'oval face','_p':P},'hair':{'text_en':'black bob','_p':P},'forms':[{'ma':'ghost_form','ten_en':'ghost form','applies_to':['KELLY'],'keeps':['face','hair'],'outfit_override':True,'image_ids':[9],'words_en':'translucent silhouette','_p':P}],'outfit':{'default':'everyday','sets':[{'id':'everyday','label':'Đồ thường','image_ids':[8],'items':[],'_p':P}]}}

@pytest.fixture
def adapter():
    with patch.object(os,'environ',{'FEATURE_KHO_FORMS_V2':'1'}):
        from core import kho_profile as k
        a={'id':1,'name':'KELLY','kind':'character','profile':json.dumps(profile()),'images':[{'id':9,'path':'ghost.png','status':'approved','role':'character_form'},{'id':8,'path':'outfit.png','status':'approved','role':'outfit'}]}
        with patch.object(k.assets,'project_assets',return_value=[a]), patch.object(k.assets,'get_profile',return_value=profile()), patch.object(k.assets,'link_characters',return_value={'KELLY':a}), patch.object(k.assets,'outfit_images',return_value=[]), patch.object(k.assets,'outfit_label',return_value=None):
            yield k,a

def test_form_and_outfit_precedence(adapter):
    k,a=adapter
    scene={'characters':['KELLY'],'byd':{'thanh_phan':[{'vat':'KELLY','dang':'ghost_form'}]}}
    f=k.forms_for_shot(None,1,scene)['KELLY']
    assert f['ma']=='ghost_form' and f['revision']==9 and f['image']['id']==9
    assert k.outfit_for(None,1,'KELLY',scene)['id']=='ghost_form'
    with patch.object(k.assets,'outfit_images',return_value=[{'id':12,'path':'project.png'}]):
        assert k.outfit_for(None,1,'KELLY',scene)['id']=='project'
    assert k.outfit_for(None,1,'KELLY')['id']=='everyday'

def test_multi_shot_does_not_spread_form(adapter):
    k,_=adapter
    rows=[{'data':{'characters':['KELLY'],'text':'ghost form'}},{'data':{'characters':['KELLY'],'text':'ordinary'}}]
    f=k.forms_for_rows(None,1,rows)['KELLY']
    assert f['shots']==[1] and f['all'] is False

def test_object_form_order_over_image_sort(adapter):
    k,a=adapter
    p=profile();p['forms'][0]['applies_to']=[]
    p['forms'].append(dict(p['forms'][0],ma='curved_deployed',ten_en='deployed',image_ids=[8]))
    a['profile']=json.dumps(p)
    assert k.selected_images(a)[0]['id']==9
    assert k.selected_images(a,{'text':'deployed'})[0]['id']==8

def test_unknown_dang_is_warning(adapter):
    k,_=adapter
    assert k.validate_dang(None,1,'KELLY','absent')[0]['muc']=='vang'

@pytest.mark.parametrize('change',[{'forms':[{'ma':'Bad key'}]}, {'hair':{'_p':{'source':'ai','state':'AUTO'}}}, {'forms':{}}, {'outfit':{'default':'absent','sets':[]}}])
def test_invalid_schema_rejected(adapter,change):
    k,_=adapter
    p=profile();p.update(change)
    with pytest.raises(k.ProfileError):k.validate(p)
