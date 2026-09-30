# Qualification-only image; build through comfy038-build.sh to pin the base ID.
ARG BASE_IMAGE=spark-comfyui:keep-h3-v035-20260930
FROM ${BASE_IMAGE}
USER root
ARG COMFY_COMMIT=6b747c0428c343e1417219641db93a4fb7cb69ae
RUN pip freeze --all | grep -vi '^comfy' > /tmp/h3-non-comfy-constraints.txt \
 && git clone https://github.com/Comfy-Org/ComfyUI.git /opt/ComfyUI-candidate \
 && git -C /opt/ComfyUI-candidate checkout --detach ${COMFY_COMMIT} \
 && test "$(git -C /opt/ComfyUI-candidate rev-parse HEAD)" = "${COMFY_COMMIT}" \
 && mv /opt/ComfyUI /opt/ComfyUI-v035-source \
 && mv /opt/ComfyUI-candidate /opt/ComfyUI \
 && pip install --constraint /tmp/h3-non-comfy-constraints.txt \
      --requirement /opt/ComfyUI/requirements.txt \
 && bash /opt/spark/build-mods.sh \
 && chown -R comfy:0 /opt/ComfyUI \
 && chmod -R g=u /opt/ComfyUI \
 && find /opt/ComfyUI -type d -exec chmod g+s {} +
LABEL org.spark-comfyui.comfy-sha=${COMFY_COMMIT}
LABEL org.plotloom.h3-runtime-qualification="2026-09-30"
WORKDIR /opt/ComfyUI
USER comfy
