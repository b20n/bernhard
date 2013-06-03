import bernhard
c = bernhard.SSLClient(host='127.0.0.1', port=5555, keyfile='example/ssl/client.pkcs8', certfile='example/ssl/client.crt', ca_certs='example/ssl/cacert.pem')

c.send({'host': 'myhost.foobar.com', 'service': 'myservice', 'metric': 12})
q = c.query('true')
