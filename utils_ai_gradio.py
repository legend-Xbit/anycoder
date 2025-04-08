import gradio as gr


def get_app(
    models: list[str],
    default_model: str,
    dropdown_label: str = "Select Hyperbolic Model",
    choices: list[str] | None = None,
    provider: str | None = None,
    bill_to: str | None = None,
    **kwargs,  # noqa: ANN003
) -> gr.Blocks:
    display_choices = choices if choices is not None else models

    def update_model(new_model: str) -> list[gr.Column]:
        if choices is not None:
            idx = display_choices.index(new_model)
            new_model = models[idx]
        return [gr.Column(visible=model_name == new_model) for model_name in models]

    with gr.Blocks(fill_height=True) as demo:
        model = gr.Dropdown(
            label=dropdown_label,
            choices=display_choices,
            value=choices[models.index(default_model)] if choices else default_model,
        )

        columns = []
        for model_name in models:
            with gr.Column(visible=model_name == default_model) as column:
                load_kwargs = {k: v for k, v in kwargs.items() if k not in ["src", "choices"]}
                if provider is not None:
                    load_kwargs["provider"] = provider
                if bill_to is not None:
                    load_kwargs["bill_to"] = bill_to
                from ai_gradio.providers import registry

                gr.load(name=model_name, src=registry, **load_kwargs)
            columns.append(column)

        model.change(
            fn=update_model,
            inputs=model,
            outputs=columns,
            api_name=False,
            queue=False,
        )

    for fn in demo.fns.values():
        fn.api_name = False

    return demo
