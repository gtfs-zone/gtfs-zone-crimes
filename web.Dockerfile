# Serves the built site as an immutable image, deployed to k3s by ArgoCD
# (gtfs-zone-infra, sites/crimes.yaml). Expects `dist/` to exist: run
# `pnpm build` first, which is what CI does before calling docker build.
#
# nginx-unprivileged listens on :8080 as uid 101 and never needs root, so the
# pod can run with runAsNonRoot + readOnlyRootFilesystem.
FROM nginxinc/nginx-unprivileged:1.29-alpine

# The image's entrypoint renders nginx.conf as an envsubst template at start,
# into /tmp, which the pod mounts writable under readOnlyRootFilesystem.
# DATA_UPSTREAM is Garage's web endpoint, which picks the bucket by the
# DATA_HOST header; the bucket has no public hostname of its own.
ENV DATA_UPSTREAM=http://garage.gtfs.svc.cluster.local:3902 \
    DATA_HOST=crimes.gtfs.zone \
    NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1 \
    NGINX_ENVSUBST_OUTPUT_DIR=/tmp

COPY nginx.conf /etc/nginx/templates/default.conf.template
RUN echo 'include /tmp/default.conf;' > /etc/nginx/conf.d/default.conf
COPY dist/ /usr/share/nginx/html/

EXPOSE 8080
