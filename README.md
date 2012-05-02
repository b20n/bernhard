# Bernhard

A simple Python client for (Riemann)[http://github.com/aphyr/riemann]. Usage:

    import bernhard
    
    c = bernhard.Client()
    c.send({'host': 'myhost.foobar.com', 'service': 'myservice', 'metric': 12})
    q = c.query('true')

