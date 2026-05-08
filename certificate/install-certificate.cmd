certutil -f -p "falcon" -importpfx My "Project Falcon.pfx"

certutil -f -addstore My "Project Falcon.cer"
certutil -f -addstore Root "Project Falcon.cer"
certutil -f -addstore TrustedPublisher "Project Falcon.cer"
