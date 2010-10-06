#!/usr/bin/env python
# -*- coding: utf-8 -*-
#    This file is part of kothic, the realtime map renderer.

#   kothic is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.

#   kothic is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.

#   You should have received a copy of the GNU General Public License
#   along with kothic.  If not, see <http://www.gnu.org/licenses/>.


from debug import debug, Timer
from mapcss import MapCSS
import sys
from libkomapnik import *

try:
        import psyco
        psyco.full()
except ImportError:
        pass

minzoom = 1
maxzoom = 19


style = MapCSS(minzoom, maxzoom)     #zoom levels
style.parse(open("styles/osmosnimki-maps.mapcss","r").read())

mapniksheet = {}

# {zoom: {z-index: [{sql:sql_hint, cond: mapnikfiltercondition, subject: subj, style: {a:b,c:d..}},{r2}...]...}...}


for zoom in range (minzoom, maxzoom):
  mapniksheet[zoom] = {}
  zsheet = mapniksheet[zoom]
  for chooser in style.choosers:
    if chooser.get_sql_hints(chooser.ruleChains[0][0].subject, zoom):
      styles = chooser.styles[0]
      zindex = styles.get("z-index",0)
      if zindex not in zsheet:
        zsheet[zindex] = []
      chooser_entry = {}
      zsheet[zindex].append(chooser_entry)
      chooser_entry["sql"] = chooser.get_sql_hints(chooser.ruleChains[0][0].subject, zoom)
      chooser_entry["style"] = styles
      chooser_entry["type"] = chooser.ruleChains[0][0].subject
      chooser_entry["rule"] = [i.conditions for i in chooser.ruleChains[0]]
      chooser_entry["chooser"] = chooser
    

#print mapniksheet

mfile = sys.stdout


mfile.write(xml_start(style.get_style("canvas", {}, maxzoom)[0].get("fill-color", "#ffffff")))
for zoom, zsheet in mapniksheet.iteritems():
  x_scale = xml_scaledenominator(zoom)
  ta = zsheet.keys()
  ta.sort(key=float)

  for zindex in ta:    
    ## areas pass
    sql = set()
    itags = set()
    xml = xml_style_start()
    for entry in zsheet[zindex]:
      if entry["type"] in ("way", "area", "polygon"):
        if "fill-color" in entry["style"]:
          xml += xml_rule_start()
          xml += x_scale
          rulestring = " or ".join([ "("+ " and ".join([i.get_mapnik_filter() for i in rule]) + ")" for rule in entry["rule"]])
          xml += xml_filter(rulestring)
          xml += xml_polygonsymbolizer(entry["style"].get("fill-color", "black"), entry["style"].get("fill-opacity", "1"))
          sql.update(entry["sql"])
          itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
          xml += xml_rule_end()
    sql = [i[1] for i in sql]
    xml += xml_style_end()
    if sql:
      mfile.write(xml)
      mfile.write(xml_layer("postgis", "polygon", itags, sql ))
    else:
      xml_nolayer()

  for zindex in ta:
    ## casings pass
    sql = set()
    itags = set()
    xml = xml_style_start()
    for entry in zsheet[zindex]:
      if entry["type"] in ("way", "line"):
        if "casing-width" in entry["style"]:
          xml += xml_rule_start()
          xml += x_scale
          rulestring = " or ".join([ "("+ " and ".join([i.get_mapnik_filter() for i in rule]) + ")" for rule in entry["rule"]])
          xml += xml_filter(rulestring)
          xml += xml_linesymbolizer(color=entry["style"].get("casing-color", "black"),
            width=float(entry["style"].get("casing-width", 1))+float(entry["style"].get("width", 0)),
            opacity=entry["style"].get("casing-opacity", "1"),
            linecap=entry["style"].get("casing-linecap", entry["style"].get("linecap","butt")),
            linejoin=entry["style"].get("casing-linejoin", entry["style"].get("linejoin", "round")))
          sql.update(entry["sql"])
          itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
          xml += xml_rule_end()
    sql = [i[1] for i in sql]
    xml += xml_style_end()
    if sql:
      mfile.write(xml)
      mfile.write(xml_layer("postgis", "line", itags, sql ))
    else:
      xml_nolayer()

  for zindex in ta:
    ## lines pass
    sql = set()
    itags = set()
    xml = xml_style_start()
    for entry in zsheet[zindex]:
      if entry["type"] in ("way", "line"):
        if "width" in entry["style"]:
          xml += xml_rule_start()
          xml += x_scale
          rulestring = " or ".join([ "("+ " and ".join([i.get_mapnik_filter() for i in rule]) + ")" for rule in entry["rule"]])
          xml += xml_filter(rulestring)
          xml += xml_linesymbolizer(color=entry["style"].get("color", "black"),
            width=entry["style"].get("width", "1"),
            opacity=entry["style"].get("opacity", "1"),
            linecap=entry["style"].get("linecap", "butt"),
            linejoin=entry["style"].get("linejoin", "round"),
            dashes=entry["style"].get("dashes", ""))
          sql.update(entry["sql"])
          itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
          xml += xml_rule_end()
    sql = [i[1] for i in sql]
    xml += xml_style_end()
    if sql:
      mfile.write(xml)
      mfile.write(xml_layer("postgis", "line", itags, sql ))
    else:
      xml_nolayer()
  for layer_type, entry_types in {"line":("way", "line"), "polygon":("way","area"), "point": ("node", "point")}.iteritems():
    for zindex in ta:
      ## icons pass
      sql = set()
      itags = set()
      xml = xml_style_start()
      for entry in zsheet[zindex]:
        if entry["type"] in entry_types:
          if "icon-image" in entry["style"]:
            xml += xml_rule_start()
            xml += x_scale
            rulestring = " or ".join([ "("+ " and ".join([i.get_mapnik_filter() for i in rule]) + ")" for rule in entry["rule"]])
            xml += xml_filter(rulestring)
            xml += xml_pointsymbolizer(
              path=entry["style"].get("icon-image", ""),
              width=entry["style"].get("icon-width", ""),
              height=entry["style"].get("icon-height", ""),
              
              opacity=entry["style"].get("opacity", "1"))

            sql.update(entry["sql"])
            itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
            xml += xml_rule_end()
      sql = [i[1] for i in sql]
      xml += xml_style_end()
      if sql:
        mfile.write(xml)
        mfile.write(xml_layer("postgis", layer_type, itags, sql ))
      else:
        xml_nolayer()
  for layer_type, entry_types in {"line":("way", "line"), "polygon":("way","area"), "point": ("node", "point")}.iteritems():
    for zindex in ta:
      ## text pass
      sql = set()
      itags = set()
      xml = xml_style_start()
      for entry in zsheet[zindex]:
        if entry["type"] in entry_types:#, "node", "line", "point"):
          if "text" in entry["style"]:
            ttext = entry["style"]["text"].extract_tags().pop()
            tface = entry["style"].get("font-family","DejaVu Sans Book")
            tsize = entry["style"].get("font-size","10")
            tcolor = entry["style"].get("text-color","#000000")
            thcolor= entry["style"].get("text-halo-color","#ffffff")
            thradius= entry["style"].get("text-halo-radius","0")
            tplace= entry["style"].get("text-position","center")
            toffset= entry["style"].get("text-offset","0")
            xml += xml_rule_start()
            xml += x_scale
            rulestring = " or ".join([ "("+ " and ".join([i.get_mapnik_filter() for i in rule]) + ")" for rule in entry["rule"]])
            xml += xml_filter(rulestring)
            xml += xml_textsymbolizer(ttext,tface,tsize,tcolor, thcolor, thradius, tplace, toffset)
            sql.update(entry["sql"])
            itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
            xml += xml_rule_end()
      sql = [i[1] for i in sql]
      xml += xml_style_end()
      if sql:
        mfile.write(xml)
        mfile.write(xml_layer("postgis", layer_type, itags, sql ))
      else:
        xml_nolayer()

mfile.write(xml_end())