---
layout: default
title: Versions
permalink: /pages/versions/
nav_order : 3
---
## Version history

{% for post in site.posts %}
  <h3><a href="{{ post.url }}">{{ post.title }}</a></h3>
  <p><span style="color: grey; font-size: small;">{{ post.date | date: "%B %d, %Y" }}</span></p>
  <p>{{ post.content | strip_html | truncatewords: 50 }}</p>
{% endfor %}
