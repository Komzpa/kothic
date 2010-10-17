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
    if chooser.get_sql_hints(chooser.ruleChains[0][0].subject, zoom)[0]:
      sys.stderr.write(str(chooser.get_sql_hints(chooser.ruleChains[0][0].subject, zoom)[0])+"\n")
      styles = chooser.styles[0]
      zindex = styles.get("z-index",0)
      if zindex not in zsheet:
        zsheet[zindex] = []
      chooser_entry = {}
      zsheet[zindex].append(chooser_entry)
      chooser_entry["sql"] = "("+ chooser.get_sql_hints(chooser.ruleChains[0][0].subject,zoom)[1] +")"
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
        if "fill-color" in entry["style"] or "fill-image" in entry["style"]:
          xml += xml_rule_start()
          xml += x_scale
          rulestring = " or ".join([ "("+ " and ".join([i.get_mapnik_filter() for i in rule]) + ")" for rule in entry["rule"]])
          xml += xml_filter(rulestring)
          if "fill-color" in entry["style"]:
            xml += xml_polygonsymbolizer(entry["style"].get("fill-color", "black"), entry["style"].get("fill-opacity", "1"))
          if "fill-image" in entry["style"]:
            xml += xml_polygonpatternsymbolizer(entry["style"].get("fill-image", ""))
          sql.add(entry["sql"])
          itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
          xml += xml_rule_end()

          

    xml += xml_style_end()
    sql.discard("()")
    if sql:
      mfile.write(xml)
      sql = " OR ".join(sql)
      mfile.write(xml_layer("postgis", "polygon", itags, sql ))
    else:
      xml_nolayer()
  for layer_type, entry_types in {"line":("way", "line"), "polygon":("way","area")}.iteritems():
    for zlayer in range(-6,7):
      for zindex in ta:
        ## casings pass
        sql = set()
        itags = set()
        xml = xml_style_start()
        for entry in zsheet[zindex]:
          if entry["type"] in entry_types:
            if "-x-mapnik-layer" in entry["style"]:
              if zlayer != -6 and entry["style"]["-x-mapnik-layer"] == "bottom":
                continue
              if zlayer != 6 and entry["style"]["-x-mapnik-layer"] == "top":
                continue
            elif zlayer not in range(-5,6):
              continue
            if "casing-width" in entry["style"]:
              xml += xml_rule_start()
              xml += x_scale
              rulestring = " or ".join([ "("+ " and ".join([i.get_mapnik_filter() for i in rule]) + ")" for rule in entry["rule"]])
              xml += xml_filter(rulestring)
              xml += xml_linesymbolizer(color=entry["style"].get("casing-color", "black"),
                width=2*float(entry["style"].get("casing-width", 1))+float(entry["style"].get("width", 0)),
                opacity=entry["style"].get("casing-opacity", entry["style"].get("opacity","1")),
                linecap=entry["style"].get("casing-linecap", entry["style"].get("linecap","butt")),
                linejoin=entry["style"].get("casing-linejoin", entry["style"].get("linejoin", "round")),
                dashes=entry["style"].get("casing-dashes",entry["style"].get("dashes", "")))

              sql.add(entry["sql"])
              itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
              xml += xml_rule_end()

        xml += xml_style_end()
        sql.discard("()")
        if sql:
          mfile.write(xml)
          sql = " OR ".join(sql)
          if zlayer == 0:
            sql = "("+ sql +') and ("layer" not in ('+ ", ".join(['\'%s\''%i for i in range(-5,6) if i != 0])+") or \"layer\" is NULL)"
          elif zlayer <=5 and zlayer >= -5:
            sql = "("+ sql +') and "layer" = \'%s\''%zlayer
          mfile.write(xml_layer("postgis", layer_type, itags, sql ))
        else:
          xml_nolayer()

      for zindex in ta:
        ## lines pass
        sql = set()
        itags = set()
        xml = xml_style_start()
        for entry in zsheet[zindex]:
          if entry["type"] in entry_types:
            if "-x-mapnik-layer" in entry["style"]:
              if zlayer != -6 and entry["style"]["-x-mapnik-layer"] == "bottom":
                continue
              if zlayer != 6 and entry["style"]["-x-mapnik-layer"] == "top":
                continue
            elif zlayer not in range(-5,6):
              continue
            if "width" in entry["style"] or "line-style" in entry["style"]:
              xml += xml_rule_start()
              xml += x_scale
              rulestring = " or ".join([ "("+ " and ".join([i.get_mapnik_filter() for i in rule]) + ")" for rule in entry["rule"]])
              xml += xml_filter(rulestring)
              if "width" in entry["style"]:
                xml += xml_linesymbolizer(color=entry["style"].get("color", "black"),
                  width=entry["style"].get("width", "1"),
                  opacity=entry["style"].get("opacity", "1"),
                  linecap=entry["style"].get("linecap", "round"),
                  linejoin=entry["style"].get("linejoin", "round"),
                  dashes=entry["style"].get("dashes", ""))
              if "line-style" in entry["style"]:
                if entry["style"]["line-style"] == "arrows":
                  xml += xml_hardcoded_arrows()
                else:
                  xml += xml_linepatternsymbolizer(entry["style"]["line-style"])
              sql.add(entry["sql"])
              itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
              xml += xml_rule_end()

        xml += xml_style_end()
        sql.discard("()")
        if sql:
          mfile.write(xml)
          sql = " OR ".join(sql)
          if zlayer == 0:
            sql = "("+ sql +') and ("layer" not in ('+ ", ".join(['\'%s\''%i for i in range(-5,6) if i != 0])+") or \"layer\" is NULL)"
          elif zlayer <=5 and zlayer >= -5:
            sql = "("+ sql +') and "layer" = \'%s\''%zlayer
          mfile.write(xml_layer("postgis", layer_type, itags, sql ))
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

            sql.add(entry["sql"])
            itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
            xml += xml_rule_end()

      xml += xml_style_end()
      sql.discard("()")
      if sql:
        mfile.write(xml)
        sql = " OR ".join(sql)
        mfile.write(xml_layer("postgis", layer_type, itags, sql ))
      else:
        xml_nolayer()
  for layer_type, entry_types in {"line":("way", "line"), "polygon":("way","area"), "point": ("node", "point")}.iteritems():
    for zindex in ta:
      ## text pass
      sql = set()
      itags = set()
      ttext = ""
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
            toverlap= entry["style"].get("text-allow-overlap",entry["style"].get("allow-overlap","false"))
            
            xml += xml_rule_start()
            xml += x_scale
            rulestring = " or ".join([ "("+ " and ".join([i.get_mapnik_filter() for i in rule]) + ")" for rule in entry["rule"]])
            xml += xml_filter(rulestring)
            xml += xml_textsymbolizer(ttext,tface,tsize,tcolor, thcolor, thradius, tplace, toffset,toverlap)
            sql.add(entry["sql"])
            itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
            xml += xml_rule_end()

      xml += xml_style_end()
      sql.discard("()")
      if sql:
        mfile.write(xml)
        if layer_type == "line":
          sqlz = " OR ".join(sql)
          itags = "\", \"".join(itags)
          itags = "\""+ itags+"\""
          sqlz = """with aaa as (SELECT %s, way FROM planet_osm_line where "%s" is not NULL and (%s)),
          bbb as (SELECT %s, way from aaa where way &amp;&amp; !bbox! )
          select %s, ST_LineMerge(ST_Union(way)) as way from bbb group by %s
          """%(itags,ttext,sqlz,itags,itags,itags)
          mfile.write(xml_layer("postgis-process", layer_type, itags, sqlz ))
        else:
          sql = " OR ".join(sql)
          mfile.write(xml_layer("postgis", layer_type, itags, sql ))
      else:
        xml_nolayer()

mfile.write(xml_end())