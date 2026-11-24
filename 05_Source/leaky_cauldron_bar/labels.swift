import AppKit

let names = ["WOOD SAGE","OLD MALT","BLACKTHORN","JUNIPER","HEARTH BITTERS","PEAR CORDIAL","SPICED MEAD","BILL OF FARE"]
let origin = ["DRY BOTANICAL SPIRIT","CELLAR RESERVE","DARK BERRY WINE","SMALL-BATCH GIN","HERBAL TINCTURE","AUTUMN PRESS","HONEY & CLOVE","ALE  •  CIDER  •  MALT"]
let size = NSSize(width:512,height:144*8)
let image = NSImage(size:size,flipped:true) { _ in
  for i in names.indices {
    let y = CGFloat(i*144)
    let paper = NSColor(calibratedRed:[0.88,0.83,0.87,0.85,0.80,0.90,0.88,0.91][i],green:0.74,blue:0.49,alpha:1)
    let ink = i%3 == 0 ? NSColor(calibratedRed:0.24,green:0.18,blue:0.105,alpha:1) : NSColor(calibratedRed:0.29,green:0.105,blue:0.075,alpha:1)
    paper.setFill()
    NSBezierPath(rect:NSRect(x:0,y:y,width:512,height:144)).fill()
    for j in 0..<145 {
      let v = (j*j*127 + 191*j + 17*i) % 503
      let r = CGFloat((j*117+89*i)%143)
      ink.withAlphaComponent(CGFloat(j%5+1)*0.017).setFill()
      NSBezierPath(ovalIn:NSRect(x:CGFloat(v),y:y+r,width:CGFloat(j%27+2),height:CGFloat(j%5+1))).fill()
    }
    ink.setStroke()
    for pad in [CGFloat(24), CGFloat(31)] {
      let box = NSBezierPath(roundedRect:NSRect(x:pad,y:y+pad*0.6,width:512-2*pad,height:144-pad*1.2),xRadius:11,yRadius:9)
      box.lineWidth = pad==24 ? 2.3 : 1
      box.stroke()
    }
    ink.setFill()
    let gem = NSBezierPath()
    gem.move(to:NSPoint(x:256,y:y+24));gem.line(to:NSPoint(x:262,y:y+31))
    gem.line(to:NSPoint(x:256,y:y+38));gem.line(to:NSPoint(x:250,y:y+31))
    gem.close();gem.fill()
    func text(_ value:String, _ face:String, _ pts:CGFloat, _ top:CGFloat, _ spacing:CGFloat) {
      let line = NSAttributedString(string:value,attributes:[
        .font:NSFont(name:face,size:pts) ?? NSFont.systemFont(ofSize:pts),
        .foregroundColor:ink,.kern:spacing
      ])
      line.draw(at:NSPoint(x:(512-line.size().width)/2,y:y+top))
    }
    text(names[i],"Georgia-Bold",33,47,2.7)
    text(origin[i],"Georgia",14,93,3.1)
  }
  return true
}
let rep = NSBitmapImageRep(data:image.tiffRepresentation!)!
try rep.representation(using:.png,properties:[:])!.write(to:URL(fileURLWithPath:CommandLine.arguments[1]),options:.atomic)
