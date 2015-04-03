# Bernhard

A simple Python client for [Riemann](http://github.com/aphyr/riemann). Usage:

```python
import bernhard

c = bernhard.Client()
c.send({'host': 'myhost.foobar.com', 'service': 'myservice', 'metric': 12})
q = c.query('true')
```

Bernhard supports custom attributes with the syntax:
```python
import bernhard

c = bernhard.Client()

c.send({'host': 'awesome.host.com', 'attributes': {'sky': 'sunny', 'sea': 'agitated'}})
```

Querying the index is as easy as:
```python
import bernhard

c = bernhard.Client()
q = c.query('true')
for e in q:
    print "Host:", e.host, "State:", e.state
```


## Installing

```bash
pip install bernhard
```

You may encounter issues with the `protobuf` dependency; if so, just run `pip
install protobuf` manually, then `pip install bernhard`.

