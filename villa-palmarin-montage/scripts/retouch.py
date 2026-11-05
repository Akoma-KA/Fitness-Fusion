import sys, os, numpy as np
from PIL import Image, ImageFilter, ImageEnhance

U="/root/.claude/uploads/164dbbcf-d142-5fe7-9f91-fd4f47a4d8f8/"
SRC={ # numéro d'origine -> fichier
1:"dcad7eda",2:"7d75e501",3:"244bad0d",4:"d5608130",5:"f17859ce",6:"70c10ecc",7:"3c6f22dd",8:"39585f95",
9:"317c3b58",10:"f5948f79",11:"e7cd4d30",12:"44432d2d",13:"02b5f299",14:"af70f9f6",15:"8b7c7542",16:"c649a056",17:"dedbac7a"}
# ordre logique Airbnb/Booking : (n° origine, nom, type)
ORDER=[(2,"facade","ext"),(1,"facade-piscine-vue-large","ext"),(7,"salon","int"),(8,"salon-et-cuisine","int"),
(5,"salon-vue-piscine","int"),(3,"salle-a-manger","int"),(4,"cuisine-equipee","int"),
(13,"chambre-1","int"),(12,"chambre-2-vue-piscine","int"),(11,"chambre-3","int"),(15,"chambre-4","int"),
(14,"salle-de-bain-1","int"),(9,"salle-de-bain-2","int"),(16,"piscine-privee","ext"),(17,"piscine-et-terrasse","ext"),(6,"piscine-pierre-volcanique","ext")]

def lum(a): return a[...,0]*0.2126+a[...,1]*0.7152+a[...,2]*0.0722

def retouch(img, kind):
    a=np.asarray(img.convert("RGB"),dtype=np.float32)/255.
    L=lum(a)
    # 1. niveaux auto (garde les couleurs)
    lo=np.percentile(L,0.4); hi=np.percentile(L,99.8)
    a=np.clip((a-lo*0.9)/(max(hi,0.6)-lo*0.9),0,1)
    L=lum(a)
    # 2. balance des blancs sur les zones neutres (murs/plafond)
    if kind=="int":
        mx=a.max(-1); mn=a.min(-1)
        m=((mx-mn)<0.16)&(L>0.35)&(L<0.92)
        if m.sum()>2000:
            mean=a[m].mean(0); g=mean.mean()
            gain=np.clip(g/mean,0.88,1.12)
            gain=1+(gain-1)*0.75
            a=a*gain
        a=a*np.array([1.025,1.0,0.965],dtype=np.float32)   # ambiance chaude
    else:
        a=a*np.array([1.012,1.0,0.99],dtype=np.float32)
    a=np.clip(a,0,1)
    # 3. ombres relevées / hautes lumières protégées
    L=lum(a)
    lift=(0.16 if kind=="int" else 0.10)*(1-L)**2.2
    a=a+lift[...,None]*(0.6+0.4*a)
    a=np.clip(a,0,1)
    a=np.where(a>0.85,0.85+(a-0.85)*0.8,a)
    # 4. courbe en S douce
    a=a+0.10*(a-0.5)*(1-np.abs(2*a-1))*2*0.5
    a=np.clip(a,0,1)
    # 5. clarté (contraste local)
    L=lum(a)
    Li=Image.fromarray((L*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(28))
    B=np.asarray(Li,dtype=np.float32)/255.
    d=(L-B)*0.30
    a=np.clip(a+d[...,None],0,1)
    out=Image.fromarray((a*255+0.5).astype(np.uint8))
    # 6. saturation + vibrance bleus/turquoise (ciel, piscine)
    out=ImageEnhance.Color(out).enhance(1.14)
    hsv=np.asarray(out.convert("HSV"),dtype=np.float32)
    h=hsv[...,0]*360/255.
    blue=np.exp(-((h-195)/38.)**2)
    hsv[...,1]=np.clip(hsv[...,1]*(1+0.22*blue),0,255)
    out=Image.fromarray(hsv.astype(np.uint8),"HSV").convert("RGB")
    # 7. netteté
    out=out.filter(ImageFilter.UnsharpMask(radius=1.1,percent=55,threshold=2))
    return out

if __name__=="__main__":
    dst=sys.argv[1]; os.makedirs(dst,exist_ok=True)
    pairs=[]
    for i,(n,name,kind) in enumerate(ORDER,1):
        im=Image.open(f"{U}{SRC[n]}-image.jpg"); im=im.convert("RGB")
        r=retouch(im,kind)
        r.save(f"{dst}/{i:02d}_{name}.jpg",quality=95,subsampling=0)
        pairs.append((im,r))
    # planche avant/après
    W=200
    rows=[]
    for k in range(0,len(pairs),4):
        row=Image.new("RGB",(W*8,int(W*1.34)),"white")
        for j,(o,r) in enumerate(pairs[k:k+4]):
            for t,im in enumerate((o,r)):
                s=im.copy(); s.thumbnail((W,int(W*1.34)))
                row.paste(s,((j*2+t)*W,0))
        rows.append(row)
    sheet=Image.new("RGB",(W*8,sum(r.height for r in rows)),"white");y=0
    for r in rows: sheet.paste(r,(0,y)); y+=r.height
    sheet.save(sys.argv[2])
    print("ok",len(pairs))
