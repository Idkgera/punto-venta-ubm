import io
import pytest
from app import create_app

@pytest.fixture
def client(tmp_path):
    app = create_app({'TESTING':True, 'DATABASE':str(tmp_path / 'test.sqlite'),
                      'UPLOAD_FOLDER':str(tmp_path / 'images'), 'SECRET_KEY':'test-secret'})
    with app.test_client() as client:
        yield client

def login(client):
    with client.session_transaction() as sess:
        sess['csrf_token']='token'
    return client.post('/login',data={'username':'admin','password':'Admin123!','csrf_token':'token'})

def create_product(client, **kwargs):
    data={'nombre':'Coca-Cola','descripcion':'600 ml','marca':'Coca-Cola','precio':'18.00','stock':'5'}
    data.update(kwargs)
    with client.session_transaction() as sess:
        token=sess['csrf_token']
    return client.post('/api/productos',data=data,headers={'X-CSRF-Token':token})

def sell(client, id, qty):
    with client.session_transaction() as sess: token=sess['csrf_token']
    return client.post('/api/vender',json={'producto_id':id,'cantidad':qty},headers={'X-CSRF-Token':token})

def test_auth_required(client):
    assert client.get('/panel').status_code==302
    assert client.get('/api/productos').status_code==401
    assert client.post('/login',data={'username':'admin','password':'wrong'}).status_code==403

def test_login_and_create(client):
    assert login(client).status_code==302
    result=create_product(client)
    assert result.status_code==201
    data=client.get('/api/productos').json['productos']
    assert len(data)==1 and data[0]['stock']==5

def test_invalid_product_values(client):
    login(client)
    assert create_product(client,precio='-3').status_code==400
    assert create_product(client,stock='-2').status_code==400
    assert create_product(client,precio='0').status_code==400
    assert create_product(client,stock='1.5').status_code==400

def test_sale_and_stock(client):
    login(client)
    id=create_product(client).json['producto']['id']
    assert sell(client,id,2).status_code==200
    assert client.get('/api/productos').json['productos'][0]['stock']==3
    assert sell(client,id,4).status_code==409
    assert client.get('/api/productos').json['productos'][0]['stock']==3
    assert client.get('/ventas').status_code==200

def test_sale_invalid_quantity(client):
    login(client)
    id=create_product(client).json['producto']['id']
    assert sell(client,id,-1).status_code==400
    assert sell(client,id,0).status_code==400
    assert sell(client,id,1.5).status_code==400

def test_upload_rejects_fake_image(client):
    login(client)
    res=create_product(client,imagen=(io.BytesIO(b'not an image'),'bad.png'))
    assert res.status_code==400

def test_login_password_change(client):
    login(client)
    with client.session_transaction() as sess:token=sess['csrf_token']
    r=client.post('/contrasena',data={'csrf_token':token,'actual':'Admin123!','nueva':'NuevaClave123'})
    assert r.status_code==302
    client.post('/logout',data={'csrf_token':token})
    with client.session_transaction() as sess: sess['csrf_token']='token'
    assert client.post('/login',data={'csrf_token':'token','username':'admin','password':'NuevaClave123'}).status_code==302
