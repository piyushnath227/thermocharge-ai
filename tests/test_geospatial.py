from app.services.geospatial import match_point_to_heatmap, feature_temperature


def test_match_point():
    heatmap = {
        'type':'FeatureCollection',
        'features':[{
            'type':'Feature',
            'properties':{'tile_id':1,'average_temperature':42.5},
            'geometry':{'type':'Polygon','coordinates':[[[-113,32],[-111,32],[-111,34],[-113,34],[-113,32]]]}
        }]
    }
    f = match_point_to_heatmap(33,-112,heatmap)
    assert f['properties']['tile_id'] == 1
    assert feature_temperature(f) == 42.5
