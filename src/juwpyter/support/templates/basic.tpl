{%- extends 'display_priority.j2' -%}
{% from 'celltags.j2' import celltags %}

{% block input_group -%}
{{ super() }}
{% endblock input_group %}

{% block input %}
{{ cell.source | highlight_code(metadata=cell.metadata) }}
{%- endblock input %}

{% block output_group %}
{{ super() }}
{% endblock output_group %}

{% block outputs %}
{{ super() }}

{% endblock outputs %}

{% block in_prompt -%}
{%- endblock in_prompt %}

{% block empty_in_prompt -%}
{%- endblock empty_in_prompt %}

{% block output_prompt %}
{% endblock output_prompt %}

{% block output_area_prompt %}
{% endblock output_area_prompt %}

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

{% block data_svg scoped -%}
<div class="jp-RenderedSVG jp-OutputArea-output {{ extra_class }}" data-mime-type="image/svg+xml">
{%- if output.svg_filename %}
<img src="{{ output.svg_filename | posix_path }}">
{%- else %}
{{ output.data['image/svg+xml'] }}
{%- endif %}
</div>
{%- endblock data_svg %}

{% block data_html scoped -%}
<div class="jp-RenderedHTMLCommon jp-RenderedHTML jp-OutputArea-output {{ extra_class }}" data-mime-type="text/html">
{{ output.data['text/html'] }}
</div>
{%- endblock data_html %}

{% block data_markdown scoped -%}
<div class="jp-RenderedHTMLCommon jp-RenderedMarkdown jp-OutputArea-output {{ extra_class }}" data-mime-type="text/markdown">
{{ output.data['text/markdown'] | markdown2html }}
</div>
{%- endblock data_markdown %}

{% block data_png scoped %}

{%- if 'image/png' in output.metadata.get('filenames', {}) %}
<img src="{{ output.metadata.filenames['image/png'] | posix_path }}"
{%- else %}
<img src="data:image/png;base64,{{ output.data['image/png'] }}"
{%- endif %}
{%- set width=output | get_metadata('width', 'image/png') -%}
{%- if width is not none %}
width={{ width }}
{%- endif %}
{%- set height=output | get_metadata('height', 'image/png') -%}
{%- if height is not none %}
height={{ height }}
{%- endif %}
{%- if output | get_metadata('unconfined', 'image/png') %}
class="unconfined"
{%- endif %}
>

{%- endblock data_png %}

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

{% block data_latex scoped %}
<div class="jp-RenderedLatex jp-OutputArea-output {{ extra_class }}" data-mime-type="text/latex">
{{ output.data['text/latex'] | e }}
</div>
{%- endblock data_latex %}

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

{%- block data_text scoped %}
<div class="jp-RenderedText jp-OutputArea-output {{ extra_class }}" data-mime-type="text/plain">
<pre>
{{- output.data['text/plain'] | ansi2html -}}
</pre>
</div>
{%- endblock -%}

{#
 ###############################################################################
 # TODO: how to better handle JavaScript repr?                                 #
 ###############################################################################
 #}

{% set div_id = uuid4() %}
{%- block data_javascript scoped %}
<div id="{{ div_id }}" class="jp-RenderedJavaScript jp-OutputArea-output {{ extra_class }}" data-mime-type="application/javascript">
<script type="text/javascript">
var element = document.getElementById('{{ div_id }}');
{{ output.data['application/javascript'] }}
</script>
</div>
{%- endblock -%}

{%- block data_widget_state scoped %}
{% set div_id = uuid4() %}
{% set datatype_list = output.data | filter_data_type %}
{% set datatype = datatype_list[0]%}
<div id="{{ div_id }}" class="output_subarea output_widget_state {{ extra_class }}">
<script type="text/javascript">
var element = document.getElementById('{{ div_id }}');
</script>
<script type="{{ datatype }}">
{{ output.data[datatype] | json_dumps }}
</script>
</div>
{%- endblock data_widget_state -%}

{%- block data_widget_view scoped %}
{% set div_id = uuid4() %}
{% set datatype_list = output.data | filter_data_type %}
{% set datatype = datatype_list[0]%}
<div id="{{ div_id }}" class="jupyter-widgets jp-OutputArea-output {{ extra_class }}">
<script type="text/javascript">
var element = document.getElementById('{{ div_id }}');
</script>
<script type="{{ datatype }}">
{{ output.data[datatype] | json_dumps }}
</script>
</div>
{%- endblock data_widget_view -%}

{%- block footer %}
{% set mimetype = 'application/vnd.jupyter.widget-state+json'%}
{% if mimetype in nb.metadata.get("widgets",{})%}
<script type="{{ mimetype }}">
{{ nb.metadata.widgets[mimetype] | json_dumps }}
</script>
{% endif %}
{{ super() }}
{%- endblock footer-%}
