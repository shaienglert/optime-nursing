from app.services.oomniker_optimizer import analyze_oomniker

def test_system_must_is_never_relaxable():
    profile={'constraints':[{'parameter':'secure_memory','authority':'SYSTEM_MUST'}]}
    out=analyze_oomniker(profile,[{}])
    assert out['system_must_immutable']==['secure_memory']
    assert not out['suggestions']

def test_client_must_requires_explicit_reconsideration():
    profile={'constraints':[{'parameter':'music_lessons','authority':'CLIENT_MUST'}]}
    rows=[{'matched_parameter_ids':['music_lessons']},{'matched_parameter_ids':[]},{'matched_parameter_ids':[]}]
    out=analyze_oomniker(profile,rows)
    s=out['suggestions'][0]
    assert s['action']=='ASK_CLIENT_TO_RECONSIDER'
    assert s['requires_client_approval'] is True
    assert s['additional_options_if_relaxed']==2

def test_preference_can_be_recommended_but_never_auto_changed():
    profile={'constraints':[{'parameter':'music_lessons','authority':'PREFERENCE'}]}
    rows=[{'matched_parameter_ids':['music_lessons']},{'matched_parameter_ids':[]}]
    s=analyze_oomniker(profile,rows)['suggestions'][0]
    assert s['action']=='RECOMMEND_TRANSPARENT_ALTERNATIVE'
    assert s['may_auto_change'] is False