#coding: utf-8
import argparse
from lxml import etree
import xmltodict
from pathlib import Path
import re
import zipfile
import os
import sys
import html
from os.path import dirname,basename,join

class Epub2Html(): 
    def __init__(self,epubpath,outputdir):
        self.epubpath = epubpath 

        script_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(script_dir,"template.html")

        self.template =Path(template_path).read_text()
        (only_name,_)=  os.path.splitext(basename(self.epubpath))
        self.only_name = only_name

        self.filedir = join(dirname(self.epubpath),only_name)
        self.absfiledir = os.path.abspath(self.filedir)
        self.outputdir =outputdir
        self.textdir = os.path.join(outputdir,only_name ,"text")

    
    def _genMemuTree(self,node,depth=0):
        for cc in node.findall("navPoint"):
            name = cc.find("./navLabel/text")
            link = cc.find("./content")
            src = link.attrib["src"]
            print("---"*depth,name.text.strip(),src)
            yield depth,name.text.strip(),src
            
        subs =node.findall("./navPoint")
        if len(subs)>0:
            for d in subs:
                yield from self._genMemuTree(d,depth+1)

    def genMemuTree(self,path):
        contents = Path(path).read_text()
        contents = contents
        print(type(contents))
        contents = re.sub(' xmlns="[^"]+"', '', contents, count=1)
        root = etree.fromstring(contents)
        print(root.tag)
        for c in root.findall("./navMap"):
            yield from self._genMemuTree(c,-1)
    def unzip(self):

        with zipfile.ZipFile(self.epubpath,'r') as zip_ref:
            zip_ref.extractall(os.path.join(self.outputdir,f"{self.only_name}"))


    def genContent(self,hash_files):
        content_list = []
        print("self.textdir",self.textdir)
        for text in  self.traverse(self.textdir):
            if text in  ["part0000.html"]:
                continue
            text = os.path.join(self.textdir,text)
            print(text)
            raw_menu = Path(text).read_text()
            raw_menu = raw_menu.encode('utf-8')
            raw_menu_dom = etree.HTML(raw_menu)
            # parts = raw_menu_dom.xpath("//body")[0]
            # for p in parts:
            raw_menu = etree.tostring(raw_menu_dom.xpath("//body")[0],pretty_print=True).decode('utf-8')
            if text in hash_files:
                print('----------------')
                raw_menu = f"<a href=\"#{self.hash(text)}\"</a>{raw_menu}"

            content_list.append(raw_menu)

        full_content = "".join(content_list)
        full_content=re.sub(r"\.\.\/images","./images",full_content)
        return full_content
        
    def traverse(self,rootdir):
        for cdirname, _, filenames in os.walk(rootdir):
            if rootdir ==  cdirname:
                return filenames 
    def hash(self, s):
        import base64
        tag = base64.b64encode(s.encode('ascii'))
        tag = tag.decode("ascii")
        return tag

    def genMenu(self,menuhtmlname):
        raw_menu =Path(join(self.textdir,menuhtmlname)).read_text()
        raw_menu = raw_menu.encode('utf-8')
        raw_menu_dom = etree.HTML(raw_menu)
        parts = raw_menu_dom.xpath("//body/*")
        raw_menus = []
        need_hash_names = []
        for p in parts:
            raw_menu = etree.tostring(p,pretty_print=True).decode('utf-8')
            # only page link, no hash jump
            a = re.search("\"part\d+.html\"",raw_menu)
            if a:
                need_hash_names.append(a.group())
                # tag = base64.b64encode(a.group().encode('ascii'))
                # tag = tag.decode("ascii")

                raw_menu = re.sub("(part\d+.html)","#"+self.hash(a.group()),raw_menu)
            else:
                raw_menu=re.sub(r"part\w+\.html","",raw_menu)
            
            raw_menus.append(raw_menu) 
        return "".join(raw_menus),need_hash_names

    
    def gen(self):
        self.unzip()
        menu, hash_files= self.genMenu("part0000.html")
        menu2, hash_files2= self.genMenu("part0001.html")

        menu =menu + menu2
        hash_files =hash_files + hash_files2

        full_content = self.genContent(hash_files)

        self.template = self.template.replace("${menu}$",menu)
        self.template = self.template.replace("${content}$",full_content)
        Path(join(self.outputdir, self.only_name,"./index.html")).write_text(self.template)
        self.copyJs()

    def copyJs(self):
        import shutil
        dest = join(self.outputdir, self.only_name,"./jquery.min.js")
        print("dest:",dest)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        jquery_path = os.path.join(script_dir,"jquery.min.js")
        shutil.copy(jquery_path,dest)


def main(args):
    filepath = args.filepath
    if filepath[0]!="." and filepath[0]!="/":
        filepath= "./"+filepath
    filepath = os.path.abspath(filepath)
    outputdir = os.path.abspath(args.outputdir)

    e = Epub2Html(filepath,outputdir)
    e.gen()

def entry_point():
    parser = createParse()
    mainArgs=parser.parse_args()
    main(mainArgs)


def createParse():
    parser = argparse.ArgumentParser( formatter_class=argparse.ArgumentDefaultsHelpFormatter, description="")
    parser.add_argument("filepath",  help="filepath" )
    parser.add_argument("outputdir",  help="outputdir" )
    return parser