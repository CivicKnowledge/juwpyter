{%- extends 'base/null.j2' -%}
{% from 'celltags.j2' import celltags %}




{%- block header -%}
{%- for author in  nb.metadata.frontmatter.authors -%}
<!-- wp:paragraph -->
<p><strong>{{ author.name }}</strong>{{ "," if not loop.last }}.</p>
<!-- /wp:paragraph -->
{%- endfor -%}
{%- if nb.metadata.frontmatter.description %}
<!-- wp:paragraph {"className":"metapack-description"} -->
<p class="metapack-description" ><em>{{ nb.metadata.frontmatter.description }}</em></p>
<!-- /wp:paragraph -->
{% endif %}
{%- if nb.metadata.frontmatter.github -%}
<!-- wp:button {"backgroundColor":"cyan-bluish-gray","className":"is-style-squared"} -->
<div class="wp-block-button is-style-squared">
<a class="wp-block-button__link has-background has-cyan-bluish-gray-background-color"
   href="{{ nb.metadata.frontmatter.github }}">
 <code>[icon name="github" class="icon-2x"]</code>
 Full notebook on github<br></a>
 </div>
<!-- /wp:button -->
{%- endif -%}
{%- endblock header -%}

{% block markdowncell scoped %}
{% if cell.heading_level -%}
<!-- wp:heading {"level":{{cell.heading_level}} } -->
<h{{cell.heading_level}}>{{ cell.source }}</h{{cell.heading_level}}>
<!-- /wp:heading -->
{%- else -%}<!-- wp:paragraph {"className":"metapack-markdown"} -->
{{ cell.source  | markdown2html | strip_files_prefix | trim }}
<!-- /wp:paragraph -->{%- endif -%}
{%- endblock markdowncell -%}

{% block codecell %}
{%- if not cell.outputs -%}
{%- set no_output_class="jp-mod-noOutputs" -%}
{%- endif -%}
{%- if not resources.global_content_filter.include_input -%}
{%- set no_input_class="jp-mod-noInput" -%}
{%- endif -%}
{{ super() }}
{%- endblock codecell %}

{% block execute_result -%}
{%- block data_priority scoped -%}
    {%- for type in output.data | filter_data_type -%}
        {%- if type == 'application/pdf' -%}
        {%- elif type == 'image/svg+xml' -%}
            {% block data_svg scoped -%}
            <div class="{{ extra_class }}" data-mime-type="image/svg+xml">
            {%- if output.svg_filename %}
            <img src="{{ output.svg_filename | posix_path }}">
            {%- else %}
            {{ output.data['image/svg+xml'] }}
            {%- endif %}
            </div>
            {%- endblock data_svg %}

        {%- elif type == 'image/png' -%}
            {% block data_png scoped %}
<!-- wp:image  {%- if width %}{"width": {{ width }} } {%- endif %} {%- if height%}{"height": {{ height }} }{%- endif %} -->
<figure class="wp-block-image">
{%- if 'image/png' in output.metadata.get('filenames', {}) %}
<img src="{{ output.metadata.filenames['image/png'] | posix_path }}" >
{%- else -%}
<img src="data:image/png;base64,{{ output.data['image/png'] }}" >"
{%- endif -%}
</figure>
<!-- /wp:image -->
            {%- endblock data_png -%}

        {%- elif type == 'text/html' -%}
            {% block data_html scoped -%}
            <!-- wp:html -->
            {{ output.data['text/html'] }}
            <!-- /wp:html -->
            {%- endblock data_html %}

        {%- elif type == 'text/markdown' -%}
            {% block data_markdown scoped -%}
            {{output}}
            <div class="{{ extra_class }}" data-mime-type="text/markdown">
            {{ output.data['text/markdown'] | markdown2html }}
            </div>
            {%- endblock data_markdown -%}

        {%- elif type == 'image/jpeg' -%}
            {% block data_jpg scoped %}
            <div class="jp-RenderedImage jp-OutputArea-output {{ extra_class }}">
            {%- if 'image/jpeg' in output.metadata.get('filenames', {}) %}
            <img src="{{ output.metadata.filenames['image/jpeg'] | posix_path }}"
            {%- else %}
            <img src="data:image/jpeg;base64,{{ output.data['image/jpeg'] }}"
            {%- endif %}
            {%- set width=output | get_metadata('width', 'image/jpeg') -%}
            {%- if width is not none %}
            width={{ width }}
            {%- endif %}
            {%- set height=output | get_metadata('height', 'image/jpeg') -%}
            {%- if height is not none %}
            height={{ height }}
            {%- endif %}
            {%- if output | get_metadata('unconfined', 'image/jpeg') %}
            class="unconfined"
            {%- endif %}
            >
            </div>
            {%- endblock data_jpg %}

        {%- elif type == 'text/plain' -%}
            {%- block data_text scoped -%}
<!-- wp:preformatted -->
<pre  class="wp-block-preformatted"> {{- output.data['text/plain'] | ansi2html -}}</pre>
<!-- /wp:preformatted -->
            {%- endblock -%}
        {%- elif type == 'text/latex' -%}
        {%- elif type == 'application/javascript' -%}
        {%- elif type == 'application/vnd.jupyter.widget-state+json' -%}}
        {%- elif type == 'application/vnd.jupyter.widget-view+json' -%}
        {%- else -%}
            {%- block data_other -%}
            {%- endblock -%}
        {%- endif -%}
    {%- endfor -%}
{%- endblock data_priority -%}
{%- endblock execute_result %}

{% block input_group -%}
{%- if cell.metadata.hide_input or nb.metadata.hide_input -%}
{%- else -%}
<!-- wp:code -->
<pre class="wp-block-code"><code>{{ cell.source }}</code></pre>
<!-- /wp:code -->
{%- endif -%}
{% endblock input_group %}

{% block output_group -%}
{%- if cell.metadata.hide_output -%}
{%- else -%}
{{ super() }}
{%- endif -%}
{% endblock output_group %}

{% block output_area_prompt %}
{% endblock output_area_prompt %}


{% block input %}
{{ cell.source | highlight_code(metadata=cell.metadata) }}
{%- endblock input %}


{% block outputs %}
{{ super() }}

{% endblock outputs %}

{% block in_prompt -%}
{%- endblock in_prompt %}

{% block empty_in_prompt -%}
{%- endblock empty_in_prompt %}

{% block output_prompt %}
{% endblock output_prompt %}

{% block output %}
{{ super() }}
{% endblock output %}


{% block unknowncell scoped %}
unknown type  {{ cell.type }}
{% endblock unknowncell %}



{% block stream_stdout -%}
{{- output.text | ansi2html -}}
{%- endblock stream_stdout %}

{% block stream_stderr -%}
{{- output.text | ansi2html -}}
{%- endblock stream_stderr %}


{% block error -%}
<div class="jp-RenderedText jp-OutputArea-output" data-mime-type="application/vnd.jupyter.stderr">
<pre>
{{- super() -}}
</pre>
</div>
{%- endblock error %}

{%- block traceback_line %}
{{ line | ansi2html }}
{%- endblock traceback_line %}


{%- block footer %}
{{ super() }}
{%- endblock footer-%}
