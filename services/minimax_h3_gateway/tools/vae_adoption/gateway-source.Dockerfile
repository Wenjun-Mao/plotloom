ARG BASE_IMAGE=plotloom-h3-gateway:before-vae-d-20261006
FROM ${BASE_IMAGE}
# Source-only overlay: preserve the exact installed gateway dependencies.
COPY services/minimax_h3_gateway/src/plotloom_h3_gateway /app/src/plotloom_h3_gateway
