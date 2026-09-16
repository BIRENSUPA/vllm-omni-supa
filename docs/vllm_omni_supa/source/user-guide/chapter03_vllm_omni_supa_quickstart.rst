快速开始
========

更多通用的 vLLM Omni 使用方法请参考 upstream vLLM Omni 的
`Quickstart <https://docs.vllm.ai/projects/vllm-omni/en/latest/>`_。

离线推理
--------

.. code-block:: python

   from vllm_omni.entrypoints.omni import Omni

    if __name__ == "__main__":
        omni = Omni(model="MiniMaxAI/MiniMax-H3")
        prompt = "a cup of coffee on the table"
        outputs = omni.generate(prompt)
        images = outputs[0].images
        images[0].save("coffee.png")

在线服务
--------

.. code-block:: shell

   vllm serve MiniMaxAI/MiniMax-H3 --omni --port 8091

.. code-block:: shell

   curl -s http://localhost:8091/v1/images/generations \
     -H "Content-Type: application/json" \
     -d '{
         "prompt": "a cup of coffee on the table",
         "size": "1024x1024",
         "response_format": "b64_json",
         "seed": 42
     }' | jq -r '.data[0].b64_json' | base64 -d > coffee.png
