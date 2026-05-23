certutil -f -p "falcon" -importpfx My "Project Falcon.pfx"

certutil -f -addstore My "Project Falcon.cer"
certutil -f -addstore -enterprise Root "Project Falcon.cer"
certutil -f -addstore -enterprise TrustedPublisher "Project Falcon.cer"
