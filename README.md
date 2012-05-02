# Bernhard

A simple Python client for [Riemann](http://github.com/aphyr/riemann). Usage:

    import bernhard
    
    c = bernhard.Client()
    c.send({'host': 'myhost.foobar.com', 'service': 'myservice', 'metric': 12})
    q = c.query('true')
    
## Installing

    pip install bernhard

You may encounter issues with the `protobuf` dependency; if so, just run `pip
install protobuf` manually, then `pip install bernhard`.

