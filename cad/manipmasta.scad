// ManipMasta - generato da cad/model.py: non modificare a mano, rigenera.
explode = 0;   // 0..1
xpos = 0;      // posizione X rullo (mm)
gap = 40;   // luce rullo-piano (mm)
$fn = 40;

dz = gap - 40;

// TAV#1 - Tavolo da pasticceria (esistente)
translate([0,0,0]) translate(explode*[0,0,-250]) {
  color([0.831,0.851,0.871]) translate([-1000.00,-400.00,-40.00]) cube([2000.00,800.00,40.00]);
  color([0.604,0.635,0.671]) translate([-985.00,-385.00,-900.00]) cube([50.00,50.00,860.00]);
  color([0.604,0.635,0.671]) translate([-985.00,335.00,-900.00]) cube([50.00,50.00,860.00]);
  color([0.604,0.635,0.671]) translate([935.00,-385.00,-900.00]) cube([50.00,50.00,860.00]);
  color([0.604,0.635,0.671]) translate([935.00,335.00,-900.00]) cube([50.00,50.00,860.00]);
  color([0.604,0.635,0.671]) translate([-960.00,-360.00,-750.00]) cube([1920.00,720.00,20.00]);
}
// IMP#1 - Palla di impasto (indicativa)
translate([0,0,0]) translate(explode*[0,0,0]) {
  color([0.902,0.769,0.541]) translate([0,0,55]) scale([110,110,55]) sphere(r=1);
}
// ANC-01#1 - Ancoraggio A1 riferimento Ø20 H7
translate([0,0,0]) translate(explode*[0,0,220]) {
  color([0.427,0.478,0.529]) translate([-980.00,-390.00,0.00]) cube([100.00,100.00,50.00]);
  color([0.200,0.227,0.259]) translate([-930.00,-340.00,50.50]) rotate([0,0,0]) cylinder(r=10.00, h=1.00, center=true);
}
// CTP-01#1 - Contropiastra sotto piano
translate([0,0,0]) translate(explode*[0,0,-280]) {
  color([0.541,0.580,0.624]) translate([-1000.00,-410.00,-45.00]) cube([140.00,140.00,5.00]);
}
// VIT-M8#1 - Viti M8×60 A2 (×4)
translate([0,0,0]) translate(explode*[0,0,-420]) {
  color([0.561,0.561,0.561]) translate([-965.00,-375.00,-20.00]) rotate([0,0,0]) cylinder(r=4.00, h=60.00, center=true);
  color([0.561,0.561,0.561]) translate([-965.00,-305.00,-20.00]) rotate([0,0,0]) cylinder(r=4.00, h=60.00, center=true);
  color([0.561,0.561,0.561]) translate([-895.00,-375.00,-20.00]) rotate([0,0,0]) cylinder(r=4.00, h=60.00, center=true);
  color([0.561,0.561,0.561]) translate([-895.00,-305.00,-20.00]) rotate([0,0,0]) cylinder(r=4.00, h=60.00, center=true);
}
// ANC-02#1 - Ancoraggio A2 asola 20 H7×26
translate([0,0,0]) translate(explode*[0,0,220]) {
  color([0.427,0.478,0.529]) translate([880.00,-390.00,0.00]) cube([100.00,100.00,50.00]);
  color([0.200,0.227,0.259]) translate([930.00,-340.00,50.50]) rotate([0,0,0]) cylinder(r=13.00, h=1.00, center=true);
}
// CTP-01#2 - Contropiastra sotto piano
translate([0,0,0]) translate(explode*[0,0,-280]) {
  color([0.541,0.580,0.624]) translate([860.00,-410.00,-45.00]) cube([140.00,140.00,5.00]);
}
// VIT-M8#2 - Viti M8×60 A2 (×4)
translate([0,0,0]) translate(explode*[0,0,-420]) {
  color([0.561,0.561,0.561]) translate([895.00,-375.00,-20.00]) rotate([0,0,0]) cylinder(r=4.00, h=60.00, center=true);
  color([0.561,0.561,0.561]) translate([895.00,-305.00,-20.00]) rotate([0,0,0]) cylinder(r=4.00, h=60.00, center=true);
  color([0.561,0.561,0.561]) translate([965.00,-375.00,-20.00]) rotate([0,0,0]) cylinder(r=4.00, h=60.00, center=true);
  color([0.561,0.561,0.561]) translate([965.00,-305.00,-20.00]) rotate([0,0,0]) cylinder(r=4.00, h=60.00, center=true);
}
// ANC-03#1 - Ancoraggio A3 appoggio Ø26
translate([0,0,0]) translate(explode*[0,0,220]) {
  color([0.427,0.478,0.529]) translate([-980.00,290.00,0.00]) cube([100.00,100.00,50.00]);
  color([0.200,0.227,0.259]) translate([-930.00,340.00,50.50]) rotate([0,0,0]) cylinder(r=13.00, h=1.00, center=true);
}
// CTP-01#3 - Contropiastra sotto piano
translate([0,0,0]) translate(explode*[0,0,-280]) {
  color([0.541,0.580,0.624]) translate([-1000.00,270.00,-45.00]) cube([140.00,140.00,5.00]);
}
// VIT-M8#3 - Viti M8×60 A2 (×4)
translate([0,0,0]) translate(explode*[0,0,-420]) {
  color([0.561,0.561,0.561]) translate([-965.00,305.00,-20.00]) rotate([0,0,0]) cylinder(r=4.00, h=60.00, center=true);
  color([0.561,0.561,0.561]) translate([-965.00,375.00,-20.00]) rotate([0,0,0]) cylinder(r=4.00, h=60.00, center=true);
  color([0.561,0.561,0.561]) translate([-895.00,305.00,-20.00]) rotate([0,0,0]) cylinder(r=4.00, h=60.00, center=true);
  color([0.561,0.561,0.561]) translate([-895.00,375.00,-20.00]) rotate([0,0,0]) cylinder(r=4.00, h=60.00, center=true);
}
// ANC-03#2 - Ancoraggio A4 appoggio Ø26
translate([0,0,0]) translate(explode*[0,0,220]) {
  color([0.427,0.478,0.529]) translate([880.00,290.00,0.00]) cube([100.00,100.00,50.00]);
  color([0.200,0.227,0.259]) translate([930.00,340.00,50.50]) rotate([0,0,0]) cylinder(r=13.00, h=1.00, center=true);
}
// CTP-01#4 - Contropiastra sotto piano
translate([0,0,0]) translate(explode*[0,0,-280]) {
  color([0.541,0.580,0.624]) translate([860.00,270.00,-45.00]) cube([140.00,140.00,5.00]);
}
// VIT-M8#4 - Viti M8×60 A2 (×4)
translate([0,0,0]) translate(explode*[0,0,-420]) {
  color([0.561,0.561,0.561]) translate([895.00,305.00,-20.00]) rotate([0,0,0]) cylinder(r=4.00, h=60.00, center=true);
  color([0.561,0.561,0.561]) translate([895.00,375.00,-20.00]) rotate([0,0,0]) cylinder(r=4.00, h=60.00, center=true);
  color([0.561,0.561,0.561]) translate([965.00,305.00,-20.00]) rotate([0,0,0]) cylinder(r=4.00, h=60.00, center=true);
  color([0.561,0.561,0.561]) translate([965.00,375.00,-20.00]) rotate([0,0,0]) cylinder(r=4.00, h=60.00, center=true);
}
// TEL-01#1 - Telaio portale saldato
translate([0,0,0]) translate(explode*[0,0,740]) {
  color([0.541,0.580,0.624]) translate([-990.00,-400.00,50.00]) cube([120.00,120.00,10.00]);
  color([0.725,0.753,0.784]) translate([-960.00,-370.00,60.00]) cube([60.00,60.00,330.00]);
  color([0.541,0.580,0.624]) translate([-990.00,280.00,50.00]) cube([120.00,120.00,10.00]);
  color([0.725,0.753,0.784]) translate([-960.00,310.00,60.00]) cube([60.00,60.00,330.00]);
  color([0.541,0.580,0.624]) translate([870.00,-400.00,50.00]) cube([120.00,120.00,10.00]);
  color([0.725,0.753,0.784]) translate([900.00,-370.00,60.00]) cube([60.00,60.00,330.00]);
  color([0.541,0.580,0.624]) translate([870.00,280.00,50.00]) cube([120.00,120.00,10.00]);
  color([0.725,0.753,0.784]) translate([900.00,310.00,60.00]) cube([60.00,60.00,330.00]);
  color([0.725,0.753,0.784]) translate([-960.00,-360.00,390.00]) cube([1920.00,40.00,80.00]);
  color([0.725,0.753,0.784]) translate([-960.00,320.00,390.00]) cube([1920.00,40.00,80.00]);
  color([0.725,0.753,0.784]) translate([-950.00,-320.00,410.00]) cube([40.00,640.00,60.00]);
  color([0.725,0.753,0.784]) translate([910.00,-320.00,410.00]) cube([40.00,640.00,60.00]);
  color([0.541,0.580,0.624]) translate([-560.00,-395.00,445.00]) cube([120.00,35.00,12.00]);
  color([0.541,0.580,0.624]) translate([440.00,-395.00,445.00]) cube([120.00,35.00,12.00]);
  color([0.541,0.580,0.624]) translate([-560.00,360.00,445.00]) cube([120.00,35.00,12.00]);
  color([0.541,0.580,0.624]) translate([440.00,360.00,445.00]) cube([120.00,35.00,12.00]);
}
// PER-01#1 - Perni di centraggio Ø20 g6 (×4)
translate([0,0,0]) translate(explode*[0,0,620]) {
  color([0.541,0.580,0.624]) translate([-930.00,-340.00,32.50]) rotate([0,0,0]) cylinder(r=10.00, h=35.00, center=true);
  color([0.541,0.580,0.624]) translate([-930.00,340.00,32.50]) rotate([0,0,0]) cylinder(r=10.00, h=35.00, center=true);
  color([0.541,0.580,0.624]) translate([930.00,-340.00,32.50]) rotate([0,0,0]) cylinder(r=10.00, h=35.00, center=true);
  color([0.541,0.580,0.624]) translate([930.00,340.00,32.50]) rotate([0,0,0]) cylinder(r=10.00, h=35.00, center=true);
}
// PBL#1 - Perno a sfere Ø8 di bloccaggio
translate([0,0,0]) translate(explode*[-80,0,60]) {
  color([0.839,0.859,0.878]) translate([-930.00,-340.00,25.00]) rotate([0,90,0]) cylinder(r=4.00, h=130.00, center=true);
  color([0.839,0.859,0.878]) translate([-1000.00,-340.00,25.00]) rotate([-90,0,0]) cylinder(r=15.00, h=4.00, center=true);
}
// PBL#2 - Perno a sfere Ø8 di bloccaggio
translate([0,0,0]) translate(explode*[-280,0,60]) {
  color([0.839,0.859,0.878]) translate([930.00,-340.00,25.00]) rotate([0,90,0]) cylinder(r=4.00, h=130.00, center=true);
  color([0.839,0.859,0.878]) translate([860.00,-340.00,25.00]) rotate([-90,0,0]) cylinder(r=15.00, h=4.00, center=true);
}
// SBR20#1 - Guide supportate SBR20 L=1800 (×2)
translate([0,0,0]) translate(explode*[0,0,580]) {
  color([0.239,0.271,0.314]) translate([-900.00,-360.00,470.00]) cube([1800.00,40.00,18.00]);
  color([0.839,0.859,0.878]) translate([0.00,-340.00,497.00]) rotate([0,90,0]) cylinder(r=10.00, h=1800.00, center=true);
  color([0.239,0.271,0.314]) translate([-900.00,320.00,470.00]) cube([1800.00,40.00,18.00]);
  color([0.839,0.859,0.878]) translate([0.00,340.00,497.00]) rotate([0,90,0]) cylinder(r=10.00, h=1800.00, center=true);
}
// SBR20UU#1 - Pattini SBR20UU (×4)
translate([xpos,0,0]) translate(explode*[0,0,560]) {
  color([0.184,0.427,0.690]) translate([-100.00,-364.00,488.00]) cube([50.00,48.00,35.00]);
  color([0.184,0.427,0.690]) translate([50.00,-364.00,488.00]) cube([50.00,48.00,35.00]);
  color([0.184,0.427,0.690]) translate([-100.00,316.00,488.00]) cube([50.00,48.00,35.00]);
  color([0.184,0.427,0.690]) translate([50.00,316.00,488.00]) cube([50.00,48.00,35.00]);
}
// CAR-01#1 - Piastra carrello X lato Y−
translate([xpos,0,0]) translate(explode*[0,0,760]) {
  color([0.773,0.800,0.827]) translate([-145.00,-400.00,523.00]) cube([290.00,220.00,12.00]);
  color([0.773,0.800,0.827]) translate([40.00,-383.00,447.00]) cube([40.00,16.00,76.00]);
  color([0.541,0.580,0.624]) translate([38.00,-386.00,446.00]) cube([44.00,22.00,6.00]);
}
// SQZ-01#1 - Squadra attacco piastra Z
translate([xpos,0,0]) translate(explode*[0,-100,400]) {
  color([0.541,0.580,0.624]) translate([-130.00,-313.00,517.00]) cube([260.00,48.00,6.00]);
  color([0.541,0.580,0.624]) translate([-130.00,-271.00,463.00]) cube([260.00,6.00,60.00]);
}
// CAR-01#2 - Piastra carrello X lato Y+
translate([xpos,0,0]) translate(explode*[0,0,760]) {
  color([0.773,0.800,0.827]) translate([-145.00,180.00,523.00]) cube([290.00,220.00,12.00]);
  color([0.773,0.800,0.827]) translate([40.00,367.00,447.00]) cube([40.00,16.00,76.00]);
  color([0.541,0.580,0.624]) translate([38.00,364.00,446.00]) cube([44.00,22.00,6.00]);
}
// SQZ-01#2 - Squadra attacco piastra Z
translate([xpos,0,0]) translate(explode*[0,100,400]) {
  color([0.541,0.580,0.624]) translate([-130.00,265.00,517.00]) cube([260.00,48.00,6.00]);
  color([0.541,0.580,0.624]) translate([-130.00,265.00,463.00]) cube([260.00,6.00,60.00]);
}
// PON-01#1 - Traversa ponte 40×40×2
translate([xpos,0,0]) translate(explode*[0,0,840]) {
  color([0.725,0.753,0.784]) translate([80.00,-400.00,535.00]) cube([40.00,800.00,40.00]);
}
// KFL#1 - Supporti flangiati KFL002 e perni di rinvio (×4)
translate([0,0,0]) translate(explode*[0,0,380]) {
  color([0.541,0.580,0.624]) translate([-915.00,-368.00,400.00]) cube([60.00,8.00,60.00]);
  color([0.541,0.580,0.624]) translate([855.00,-368.00,400.00]) cube([60.00,8.00,60.00]);
  color([0.541,0.580,0.624]) translate([-915.00,360.00,400.00]) cube([60.00,8.00,60.00]);
  color([0.541,0.580,0.624]) translate([855.00,360.00,400.00]) cube([60.00,8.00,60.00]);
}
// ASS-X#1 - Albero di sincronismo Ø16
translate([0,0,0]) translate(explode*[0,-500,380]) {
  color([0.561,0.561,0.561]) translate([-885.00,0.00,430.00]) rotate([-90,0,0]) cylinder(r=8.00, h=900.00, center=true);
}
// PUL-X#1 - Pulegge HTD-5M 20T motrici e di rinvio (×4)
translate([0,0,0]) translate(explode*[0,0,500]) {
  color([0.655,0.678,0.702]) translate([-885.00,-375.00,430.00]) rotate([-90,0,0]) cylinder(r=17.00, h=22.00, center=true);
  color([0.655,0.678,0.702]) translate([885.00,-375.00,430.00]) rotate([-90,0,0]) cylinder(r=17.00, h=22.00, center=true);
  color([0.655,0.678,0.702]) translate([-885.00,375.00,430.00]) rotate([-90,0,0]) cylinder(r=17.00, h=22.00, center=true);
  color([0.655,0.678,0.702]) translate([885.00,375.00,430.00]) rotate([-90,0,0]) cylinder(r=17.00, h=22.00, center=true);
}
// BELT-X#1 - Cinghie aperte HTD-5M larghezza 15 (×2)
translate([0,0,0]) translate(explode*[0,0,440]) {
  color([0.082,0.082,0.082]) translate([-885.00,-382.50,445.00]) cube([1770.00,15.00,2.50]);
  color([0.082,0.082,0.082]) translate([-885.00,-382.50,412.50]) cube([1770.00,15.00,2.50]);
  color([0.082,0.082,0.082]) translate([-885.00,367.50,445.00]) cube([1770.00,15.00,2.50]);
  color([0.082,0.082,0.082]) translate([-885.00,367.50,412.50]) cube([1770.00,15.00,2.50]);
}
// MOT-X#1 - Motore X NEMA23 closed-loop (M1)
translate([0,0,0]) translate(explode*[0,370,380]) {
  color([0.604,0.631,0.659]) translate([-913.50,465.00,401.50]) cube([57.00,8.00,57.00]);
  color([0.141,0.153,0.169]) translate([-913.00,473.00,402.00]) cube([56.00,76.00,56.00]);
  color([0.227,0.247,0.275]) translate([-912.00,549.00,403.00]) cube([54.00,22.00,54.00]);
  color([0.604,0.631,0.659]) translate([-910.00,571.00,405.00]) cube([50.00,6.00,50.00]);
  color([0.839,0.859,0.878]) translate([-885.00,454.00,430.00]) rotate([-90,0,0]) cylinder(r=4.00, h=22.00, center=true);
  color([0.333,0.357,0.384]) translate([-892.00,531.00,456.00]) cube([14.00,16.00,14.00]);
  color([0.773,0.800,0.827]) translate([-925.00,465.00,390.00]) cube([80.00,8.00,80.00]);
  color([0.773,0.800,0.827]) translate([-925.00,437.00,470.00]) cube([80.00,36.00,6.00]);
}
// GIU-X#1 - Giunto elastico 8→14
translate([0,0,0]) translate(explode*[0,290,380]) {
  color([0.753,0.224,0.169]) translate([-885.00,425.00,430.00]) rotate([-90,0,0]) cylinder(r=16.00, h=34.00, center=true);
}
// ZPL-01#1 - Piastra Z fissa lato Y−
translate([xpos,0,0]) translate(explode*[0,-300,560]) {
  color([0.773,0.800,0.827]) translate([-145.00,-265.00,130.00]) cube([290.00,15.00,393.00]);
}
// SUP-Z#1 - Supporti SK16 (×4) e BK12/BF12 lato Y−
translate([xpos,0,0]) translate(explode*[0,-40,560]) {
  color([0.604,0.639,0.678]) translate([-136.00,-250.00,135.00]) cube([42.00,36.00,14.00]);
  color([0.604,0.639,0.678]) translate([-136.00,-250.00,486.00]) cube([42.00,36.00,14.00]);
  color([0.604,0.639,0.678]) translate([94.00,-250.00,135.00]) cube([42.00,36.00,14.00]);
  color([0.604,0.639,0.678]) translate([94.00,-250.00,486.00]) cube([42.00,36.00,14.00]);
  color([0.478,0.522,0.565]) translate([-95.00,-250.00,137.00]) cube([60.00,28.00,22.00]);
  color([0.478,0.522,0.565]) translate([-95.00,-250.00,468.00]) cube([60.00,28.00,30.00]);
}
// ZPL-01#2 - Piastra Z fissa lato Y+
translate([xpos,0,0]) translate(explode*[0,300,560]) {
  color([0.773,0.800,0.827]) translate([-145.00,250.00,130.00]) cube([290.00,15.00,393.00]);
}
// SUP-Z#2 - Supporti SK16 (×4) e BK12/BF12 lato Y+
translate([xpos,0,0]) translate(explode*[0,40,560]) {
  color([0.604,0.639,0.678]) translate([-136.00,214.00,135.00]) cube([42.00,36.00,14.00]);
  color([0.604,0.639,0.678]) translate([-136.00,214.00,486.00]) cube([42.00,36.00,14.00]);
  color([0.604,0.639,0.678]) translate([94.00,214.00,135.00]) cube([42.00,36.00,14.00]);
  color([0.604,0.639,0.678]) translate([94.00,214.00,486.00]) cube([42.00,36.00,14.00]);
  color([0.478,0.522,0.565]) translate([-95.00,222.00,137.00]) cube([60.00,28.00,22.00]);
  color([0.478,0.522,0.565]) translate([-95.00,222.00,468.00]) cube([60.00,28.00,30.00]);
}
// ZSL-01#1 - Slitta Z lato Y− (porta motore R)
translate([xpos,0,dz]) translate(explode*[0,-320,360]) {
  color([0.773,0.800,0.827]) translate([-150.00,-203.00,50.00]) cube([300.00,16.00,250.00]);
  color([0.773,0.800,0.827]) translate([150.00,-200.00,286.00]) cube([16.00,10.00,14.00]);
}
// SC16UU#1 - Pattini SC16UU (×4) lato Y−
translate([xpos,0,dz]) translate(explode*[0,-400,360]) {
  color([0.184,0.427,0.690]) translate([-136.00,-243.00,192.00]) cube([42.00,40.00,36.00]);
  color([0.184,0.427,0.690]) translate([-136.00,-243.00,252.00]) cube([42.00,40.00,36.00]);
  color([0.184,0.427,0.690]) translate([94.00,-243.00,192.00]) cube([42.00,40.00,36.00]);
  color([0.184,0.427,0.690]) translate([94.00,-243.00,252.00]) cube([42.00,40.00,36.00]);
}
// NUT-Z#1 - Chiocciola TR16×4 con supporto lato Y−
translate([xpos,0,dz]) translate(explode*[0,-400,420]) {
  color([0.541,0.580,0.624]) translate([-90.00,-243.00,220.00]) cube([50.00,40.00,40.00]);
  color([0.690,0.553,0.227]) translate([-65.00,-223.00,240.00]) rotate([0,0,0]) cylinder(r=15.00, h=46.00, center=true);
}
// BRG-6204#1 - Cuscinetto inox S6204-2RS + coperchio lato Y−
translate([xpos,0,dz]) translate(explode*[0,-320,300]) {
  color([0.498,0.545,0.592]) translate([0.00,-195.00,90.00]) rotate([-90,0,0]) cylinder(r=23.50, h=14.00, center=true);
  color([0.541,0.580,0.624]) translate([0.00,-205.50,90.00]) rotate([-90,0,0]) cylinder(r=36.00, h=5.00, center=true);
}
// ZSL-02#1 - Slitta Z lato Y+
translate([xpos,0,dz]) translate(explode*[0,320,360]) {
  color([0.773,0.800,0.827]) translate([-150.00,187.00,50.00]) cube([300.00,16.00,250.00]);
  color([0.773,0.800,0.827]) translate([150.00,190.00,286.00]) cube([16.00,10.00,14.00]);
}
// SC16UU#2 - Pattini SC16UU (×4) lato Y+
translate([xpos,0,dz]) translate(explode*[0,400,360]) {
  color([0.184,0.427,0.690]) translate([-136.00,203.00,192.00]) cube([42.00,40.00,36.00]);
  color([0.184,0.427,0.690]) translate([-136.00,203.00,252.00]) cube([42.00,40.00,36.00]);
  color([0.184,0.427,0.690]) translate([94.00,203.00,192.00]) cube([42.00,40.00,36.00]);
  color([0.184,0.427,0.690]) translate([94.00,203.00,252.00]) cube([42.00,40.00,36.00]);
}
// NUT-Z#2 - Chiocciola TR16×4 con supporto lato Y+
translate([xpos,0,dz]) translate(explode*[0,400,420]) {
  color([0.541,0.580,0.624]) translate([-90.00,203.00,220.00]) cube([50.00,40.00,40.00]);
  color([0.690,0.553,0.227]) translate([-65.00,223.00,240.00]) rotate([0,0,0]) cylinder(r=15.00, h=46.00, center=true);
}
// BRG-6204#2 - Cuscinetto inox S6204-2RS + coperchio lato Y+
translate([xpos,0,dz]) translate(explode*[0,320,300]) {
  color([0.498,0.545,0.592]) translate([0.00,195.00,90.00]) rotate([-90,0,0]) cylinder(r=23.50, h=14.00, center=true);
  color([0.541,0.580,0.624]) translate([0.00,205.50,90.00]) rotate([-90,0,0]) cylinder(r=36.00, h=5.00, center=true);
}
// RUL-01#1 - Rullo Ø100 L=360 con perni Ø20
translate([xpos,0,dz]) translate(explode*[0,0,220]) {
  color([0.933,0.945,0.957]) translate([0.00,0.00,90.00]) rotate([-90,0,0]) cylinder(r=50.00, h=360.00, center=true);
  color([0.725,0.753,0.784]) translate([0.00,-206.50,90.00]) rotate([-90,0,0]) cylinder(r=10.00, h=53.00, center=true);
  color([0.725,0.753,0.784]) translate([0.00,195.50,90.00]) rotate([-90,0,0]) cylinder(r=10.00, h=31.00, center=true);
}
// ALB-Z#1 - Alberi Ø16 h6 (×2) lato Y−
translate([xpos,0,0]) translate(explode*[0,-90,900]) {
  color([0.839,0.859,0.878]) translate([-115.00,-223.00,316.50]) rotate([0,0,0]) cylinder(r=8.00, h=367.00, center=true);
  color([0.839,0.859,0.878]) translate([115.00,-223.00,316.50]) rotate([0,0,0]) cylinder(r=8.00, h=367.00, center=true);
}
// VIT-Z#1 - Vite trapezia TR16×4 lato Y−
translate([xpos,0,0]) translate(explode*[0,-90,940]) {
  color([0.561,0.561,0.561]) translate([-65.00,-223.00,347.50]) rotate([0,0,0]) cylinder(r=8.00, h=419.00, center=true);
}
// ALB-Z#2 - Alberi Ø16 h6 (×2) lato Y+
translate([xpos,0,0]) translate(explode*[0,90,900]) {
  color([0.839,0.859,0.878]) translate([-115.00,223.00,316.50]) rotate([0,0,0]) cylinder(r=8.00, h=367.00, center=true);
  color([0.839,0.859,0.878]) translate([115.00,223.00,316.50]) rotate([0,0,0]) cylinder(r=8.00, h=367.00, center=true);
}
// VIT-Z#2 - Vite trapezia TR16×4 lato Y+
translate([xpos,0,0]) translate(explode*[0,90,940]) {
  color([0.561,0.561,0.561]) translate([-65.00,223.00,347.50]) rotate([0,0,0]) cylinder(r=8.00, h=419.00, center=true);
}
// GIU-Z#1 - Giunto elastico 8→12 lato Y−
translate([xpos,0,0]) translate(explode*[0,-90,820]) {
  color([0.753,0.224,0.169]) translate([-65.00,-223.00,557.00]) rotate([0,0,0]) cylinder(r=12.50, h=30.00, center=true);
}
// STM-01#1 - Flangia motore + distanziali 40 mm lato Y−
translate([xpos,0,0]) translate(explode*[0,-90,930]) {
  color([0.725,0.753,0.784]) translate([-88.60,-246.60,555.00]) rotate([0,0,0]) cylinder(r=6.00, h=40.00, center=true);
  color([0.725,0.753,0.784]) translate([-88.60,-199.40,555.00]) rotate([0,0,0]) cylinder(r=6.00, h=40.00, center=true);
  color([0.725,0.753,0.784]) translate([-41.40,-246.60,555.00]) rotate([0,0,0]) cylinder(r=6.00, h=40.00, center=true);
  color([0.725,0.753,0.784]) translate([-41.40,-199.40,555.00]) rotate([0,0,0]) cylinder(r=6.00, h=40.00, center=true);
  color([0.773,0.800,0.827]) translate([-105.00,-263.00,575.00]) cube([80.00,80.00,10.00]);
}
// MOT-Z#1 - Motore Z1 NEMA23 closed-loop (M2)
translate([xpos,0,0]) translate(explode*[0,-90,990]) {
  color([0.604,0.631,0.659]) translate([-93.50,-251.50,585.00]) cube([57.00,57.00,8.00]);
  color([0.141,0.153,0.169]) translate([-93.00,-251.00,593.00]) cube([56.00,56.00,76.00]);
  color([0.227,0.247,0.275]) translate([-92.00,-250.00,669.00]) cube([54.00,54.00,22.00]);
  color([0.604,0.631,0.659]) translate([-90.00,-248.00,691.00]) cube([50.00,50.00,6.00]);
  color([0.839,0.859,0.878]) translate([-65.00,-223.00,574.00]) rotate([0,0,0]) cylinder(r=4.00, h=22.00, center=true);
  color([0.333,0.357,0.384]) translate([-39.00,-230.00,651.00]) cube([14.00,14.00,16.00]);
}
// GIU-Z#2 - Giunto elastico 8→12 lato Y+
translate([xpos,0,0]) translate(explode*[0,90,820]) {
  color([0.753,0.224,0.169]) translate([-65.00,223.00,557.00]) rotate([0,0,0]) cylinder(r=12.50, h=30.00, center=true);
}
// STM-01#2 - Flangia motore + distanziali 40 mm lato Y+
translate([xpos,0,0]) translate(explode*[0,90,930]) {
  color([0.725,0.753,0.784]) translate([-88.60,199.40,555.00]) rotate([0,0,0]) cylinder(r=6.00, h=40.00, center=true);
  color([0.725,0.753,0.784]) translate([-88.60,246.60,555.00]) rotate([0,0,0]) cylinder(r=6.00, h=40.00, center=true);
  color([0.725,0.753,0.784]) translate([-41.40,199.40,555.00]) rotate([0,0,0]) cylinder(r=6.00, h=40.00, center=true);
  color([0.725,0.753,0.784]) translate([-41.40,246.60,555.00]) rotate([0,0,0]) cylinder(r=6.00, h=40.00, center=true);
  color([0.773,0.800,0.827]) translate([-105.00,183.00,575.00]) cube([80.00,80.00,10.00]);
}
// MOT-Z#2 - Motore Z2 NEMA23 closed-loop (M3)
translate([xpos,0,0]) translate(explode*[0,90,990]) {
  color([0.604,0.631,0.659]) translate([-93.50,194.50,585.00]) cube([57.00,57.00,8.00]);
  color([0.141,0.153,0.169]) translate([-93.00,195.00,593.00]) cube([56.00,56.00,76.00]);
  color([0.227,0.247,0.275]) translate([-92.00,196.00,669.00]) cube([54.00,54.00,22.00]);
  color([0.604,0.631,0.659]) translate([-90.00,198.00,691.00]) cube([50.00,50.00,6.00]);
  color([0.839,0.859,0.878]) translate([-65.00,223.00,574.00]) rotate([0,0,0]) cylinder(r=4.00, h=22.00, center=true);
  color([0.333,0.357,0.384]) translate([-39.00,216.00,651.00]) cube([14.00,14.00,16.00]);
}
// PUL-R#1 - Puleggia HTD-5M 40T sul perno rullo
translate([xpos,0,dz]) translate(explode*[0,-260,420]) {
  color([0.655,0.678,0.702]) translate([0.00,-220.00,90.00]) rotate([-90,0,0]) cylinder(r=33.00, h=22.00, center=true);
}
// MOT-R#1 - Motore R rotazione rullo NEMA23 closed-loop (M4)
translate([xpos,0,dz]) translate(explode*[0,320,420]) {
  color([0.604,0.631,0.659]) translate([-28.50,-187.00,196.50]) cube([57.00,8.00,57.00]);
  color([0.141,0.153,0.169]) translate([-28.00,-179.00,197.00]) cube([56.00,76.00,56.00]);
  color([0.227,0.247,0.275]) translate([-27.00,-103.00,198.00]) cube([54.00,22.00,54.00]);
  color([0.604,0.631,0.659]) translate([-25.00,-81.00,200.00]) cube([50.00,6.00,50.00]);
  color([0.839,0.859,0.878]) translate([0.00,-198.00,225.00]) rotate([-90,0,0]) cylinder(r=4.00, h=22.00, center=true);
  color([0.333,0.357,0.384]) translate([-7.00,-121.00,251.00]) cube([14.00,16.00,14.00]);
  color([0.655,0.678,0.702]) translate([0.00,-220.00,225.00]) rotate([-90,0,0]) cylinder(r=17.00, h=22.00, center=true);
}
// BELT-R#1 - Cinghia chiusa HTD 425-5M-15
translate([xpos,0,dz]) translate(explode*[0,-200,420]) {
  color([0.082,0.082,0.082]) translate([-26.50,-227.50,90.00]) cube([3.00,15.00,135.00]);
  color([0.082,0.082,0.082]) translate([23.50,-227.50,90.00]) cube([3.00,15.00,135.00]);
}
// RAS-01#1 - Raschietto POM-C con barra di supporto
translate([xpos,0,dz]) translate(explode*[-260,0,300]) {
  color([0.953,0.945,0.918]) translate([-61.00,-175.00,100.00]) cube([10.00,350.00,40.00]);
  color([0.541,0.580,0.624]) translate([-68.00,-187.00,140.00]) cube([8.00,374.00,16.00]);
}
// SEN-X#1 - Finecorsa X_MIN / X_MAX induttivi M12
translate([0,0,0]) translate(explode*[0,-60,500]) {
  color([0.878,0.690,0.000]) translate([-845.00,-295.00,495.00]) rotate([0,0,0]) cylinder(r=6.00, h=40.00, center=true);
  color([0.541,0.580,0.624]) translate([-855.00,-322.00,476.00]) cube([20.00,30.00,4.00]);
  color([0.878,0.690,0.000]) translate([845.00,-295.00,495.00]) rotate([0,0,0]) cylinder(r=6.00, h=40.00, center=true);
  color([0.541,0.580,0.624]) translate([835.00,-322.00,476.00]) cube([20.00,30.00,4.00]);
}
// SEN-Z#1 - Sensori Z HOME (alto) e LOW (basso) lato Y−
translate([xpos,0,0]) translate(explode*[60,-140,560]) {
  color([0.878,0.690,0.000]) translate([158.00,-225.00,403.00]) rotate([-90,0,0]) cylinder(r=6.00, h=40.00, center=true);
  color([0.878,0.690,0.000]) translate([158.00,-225.00,253.50]) rotate([-90,0,0]) cylinder(r=6.00, h=40.00, center=true);
}
// SEN-Z#2 - Sensori Z HOME (alto) e LOW (basso) lato Y+
translate([xpos,0,0]) translate(explode*[60,140,560]) {
  color([0.878,0.690,0.000]) translate([158.00,225.00,403.00]) rotate([-90,0,0]) cylinder(r=6.00, h=40.00, center=true);
  color([0.878,0.690,0.000]) translate([158.00,225.00,253.50]) rotate([-90,0,0]) cylinder(r=6.00, h=40.00, center=true);
}
// SEN-SEAT#1 - Sensori 'portale in sede' M12 (×2)
translate([0,0,0]) translate(explode*[0,0,410]) {
  color([0.878,0.690,0.000]) translate([-885.00,-385.00,85.00]) rotate([0,0,0]) cylinder(r=6.00, h=50.00, center=true);
  color([0.878,0.690,0.000]) translate([975.00,-385.00,85.00]) rotate([0,0,0]) cylinder(r=6.00, h=50.00, center=true);
}
// CAN-01#1 - Canalina di guida catena (lato Y−)
translate([0,0,0]) translate(explode*[0,-300,300]) {
  color([0.541,0.580,0.624]) translate([-760.00,-460.00,435.00]) cube([1520.00,50.00,3.00]);
  color([0.541,0.580,0.624]) translate([-760.00,-460.00,435.00]) cube([1520.00,3.00,30.00]);
  color([0.541,0.580,0.624]) translate([-760.00,-413.00,435.00]) cube([1520.00,3.00,30.00]);
  color([0.541,0.580,0.624]) translate([-615.00,-447.50,433.00]) cube([30.00,100.00,6.00]);
  color([0.541,0.580,0.624]) translate([-15.00,-447.50,433.00]) cube([30.00,100.00,6.00]);
  color([0.541,0.580,0.624]) translate([585.00,-447.50,433.00]) cube([30.00,100.00,6.00]);
}
// CHAIN#1 - Catena portacavi 15×30 R48
translate([0,0,0]) translate(explode*[0,-150,500]) {
  color([0.290,0.310,0.341]) translate([0.00,-454.00,438.00]) cube([365.00,38.00,24.00]);
  color([0.290,0.310,0.341]) translate([0.00,-454.00,495.00]) cube([365.00,38.00,24.00]);
}
// STF-CAT#1 - Staffa catena sul carrello
translate([xpos,0,0]) translate(explode*[0,-250,560]) {
  color([0.541,0.580,0.624]) translate([-40.00,-460.00,517.00]) cube([80.00,60.00,6.00]);
}
// QE-01#1 - Cassetta inox IP65 500×400×250 con staffe
translate([0,0,0]) translate(explode*[-510,0,300]) {
  color([0.812,0.835,0.859]) translate([-1253.00,-250.00,100.00]) cube([248.00,500.00,2.00]);
  color([0.812,0.835,0.859]) translate([-1253.00,-250.00,498.00]) cube([248.00,500.00,2.00]);
  color([0.812,0.835,0.859]) translate([-1007.00,-250.00,100.00]) cube([2.00,500.00,400.00]);
  color([0.812,0.835,0.859]) translate([-1253.00,-250.00,100.00]) cube([248.00,2.00,400.00]);
  color([0.812,0.835,0.859]) translate([-1253.00,248.00,100.00]) cube([248.00,2.00,400.00]);
  color([0.541,0.580,0.624]) translate([-1005.00,-210.00,430.00]) cube([55.00,20.00,20.00]);
  color([0.541,0.580,0.624]) translate([-1005.00,190.00,430.00]) cube([55.00,20.00,20.00]);
}
// QE-DOOR#1 - Porta con fungo emergenza S0, reset S1, START S2, STOP S3
translate([0,0,0]) translate(explode*[-620,0,300]) {
  color([0.812,0.835,0.859]) translate([-1255.00,-250.00,100.00]) cube([2.00,500.00,400.00]);
  color([0.831,0.125,0.125]) translate([-1267.00,-120.00,400.00]) rotate([0,90,0]) cylinder(r=20.00, h=22.00, center=true);
  color([0.949,0.761,0.000]) translate([-1259.00,-120.00,400.00]) rotate([0,90,0]) cylinder(r=30.00, h=4.00, center=true);
  color([0.118,0.435,0.816]) translate([-1261.00,-190.00,400.00]) rotate([0,90,0]) cylinder(r=12.00, h=12.00, center=true);
  color([0.165,0.604,0.227]) translate([-1261.00,-120.00,310.00]) rotate([0,90,0]) cylinder(r=12.00, h=12.00, center=true);
  color([0.125,0.125,0.125]) translate([-1261.00,-190.00,310.00]) rotate([0,90,0]) cylinder(r=12.00, h=12.00, center=true);
  color([0.604,0.631,0.659]) translate([-1262.00,192.00,270.00]) cube([6.00,16.00,60.00]);
  color([0.188,0.208,0.231]) translate([-1250.00,-135.00,380.00]) cube([50.00,30.00,40.00]);
  color([0.188,0.208,0.231]) translate([-1250.00,-205.00,380.00]) cube([50.00,30.00,40.00]);
  color([0.188,0.208,0.231]) translate([-1250.00,-135.00,290.00]) cube([50.00,30.00,40.00]);
  color([0.188,0.208,0.231]) translate([-1250.00,-205.00,290.00]) cube([50.00,30.00,40.00]);
}
// H1#1 - Colonna luminosa 24 V verde/giallo/rosso + buzzer
translate([0,0,0]) translate(explode*[-260,0,570]) {
  color([0.604,0.631,0.659]) translate([-1045.00,200.00,515.00]) rotate([0,0,0]) cylinder(r=20.00, h=30.00, center=true);
  color([0.188,0.627,0.251]) translate([-1045.00,200.00,545.00]) rotate([0,0,0]) cylinder(r=20.00, h=30.00, center=true);
  color([0.878,0.690,0.000]) translate([-1045.00,200.00,575.00]) rotate([0,0,0]) cylinder(r=20.00, h=30.00, center=true);
  color([0.831,0.125,0.125]) translate([-1045.00,200.00,605.00]) rotate([0,0,0]) cylinder(r=20.00, h=30.00, center=true);
}
// XP#1 - Connettori Harting XP1 (motori/encoder) e XP2 (sensori), pressacavi
translate([0,0,0]) translate(explode*[-260,0,50]) {
  color([0.482,0.522,0.561]) translate([-1220.00,-81.50,30.00]) cube([90.00,43.00,70.00]);
  color([0.482,0.522,0.561]) translate([-1210.00,-77.50,8.00]) cube([70.00,35.00,24.00]);
  color([0.482,0.522,0.561]) translate([-1210.00,50.00,40.00]) cube([70.00,40.00,60.00]);
  color([0.482,0.522,0.561]) translate([-1202.50,54.00,19.00]) cube([55.00,32.00,22.00]);
  color([0.169,0.184,0.200]) translate([-1075.00,-150.00,88.00]) rotate([0,0,0]) cylinder(r=15.00, h=24.00, center=true);
  color([0.169,0.184,0.200]) translate([-1075.00,150.00,88.00]) rotate([0,0,0]) cylinder(r=12.00, h=24.00, center=true);
}
// CAV-01#1 - Fascio cavi quadro → catena portacavi
translate([0,0,0]) translate(explode*[0,-270,300]) {
  color([0.125,0.137,0.149]) hull() { translate([-1175.0, -60, 8]) sphere(r=11.0); translate([-1175.0, -60, -15]) sphere(r=11.0); }
  color([0.125,0.137,0.149]) hull() { translate([-1175.0, -60, -15]) sphere(r=11.0); translate([-1175.0, -275.0, -15]) sphere(r=11.0); }
  color([0.125,0.137,0.149]) hull() { translate([-1175.0, -275.0, -15]) sphere(r=11.0); translate([-1175.0, -275.0, 445.0]) sphere(r=11.0); }
  color([0.125,0.137,0.149]) hull() { translate([-1175.0, -275.0, 445.0]) sphere(r=11.0); translate([-985.0, -275.0, 445.0]) sphere(r=11.0); }
  color([0.125,0.137,0.149]) hull() { translate([-985.0, -275.0, 445.0]) sphere(r=11.0); translate([-985.0, -435.0, 445.0]) sphere(r=11.0); }
  color([0.125,0.137,0.149]) hull() { translate([-985.0, -435.0, 445.0]) sphere(r=11.0); translate([-20, -435.0, 445.0]) sphere(r=11.0); }
}
// QE-PIA#1 - Piastra di fondo, canaline 40×25, guide DIN
translate([0,0,0]) translate(explode*[-260,0,300]) {
  color([0.875,0.890,0.906]) translate([-1010.00,-242.00,108.00]) cube([3.00,484.00,384.00]);
  color([0.765,0.784,0.804]) translate([-1050.00,-222.00,462.00]) cube([40.00,444.00,25.00]);
  color([0.765,0.784,0.804]) translate([-1050.00,-222.00,322.00]) cube([40.00,444.00,25.00]);
  color([0.765,0.784,0.804]) translate([-1050.00,-222.00,120.00]) cube([40.00,444.00,25.00]);
  color([0.765,0.784,0.804]) translate([-1050.00,230.00,120.00]) cube([40.00,18.00,367.00]);
  color([0.765,0.784,0.804]) translate([-1050.00,-248.00,120.00]) cube([40.00,18.00,367.00]);
  color([0.839,0.859,0.878]) translate([-1018.00,-215.00,402.00]) cube([8.00,430.00,10.00]);
  color([0.839,0.859,0.878]) translate([-1018.00,-145.00,232.00]) cube([8.00,360.00,10.00]);
}
// QE-DIN#1 - Fila potenza: X0, Q1, Q2, F1–F5, KM1+KM2, K1 sicurezza, F11–F14, X1, X2
translate([0,0,0]) translate(explode*[-380,0,300]) {
  color([0.541,0.561,0.600]) translate([-1080.00,191.00,362.00]) cube([70.00,24.00,90.00]);
  color([0.933,0.933,0.925]) translate([-1085.00,153.00,362.00]) cube([75.00,36.00,90.00]);
  color([0.933,0.933,0.925]) translate([-1085.00,115.00,362.00]) cube([75.00,36.00,90.00]);
  color([0.933,0.933,0.925]) translate([-1080.00,95.00,362.00]) cube([70.00,18.00,90.00]);
  color([0.933,0.933,0.925]) translate([-1080.00,75.00,362.00]) cube([70.00,18.00,90.00]);
  color([0.933,0.933,0.925]) translate([-1080.00,55.00,362.00]) cube([70.00,18.00,90.00]);
  color([0.604,0.647,0.694]) translate([-1095.00,8.00,362.00]) cube([85.00,45.00,90.00]);
  color([0.604,0.647,0.694]) translate([-1095.00,-39.00,362.00]) cube([85.00,45.00,90.00]);
  color([0.949,0.761,0.000]) translate([-1125.00,-63.50,362.00]) cube([115.00,22.50,90.00]);
  color([0.933,0.933,0.925]) translate([-1080.00,-83.50,362.00]) cube([70.00,18.00,90.00]);
  color([0.933,0.933,0.925]) translate([-1080.00,-103.50,362.00]) cube([70.00,18.00,90.00]);
  color([0.933,0.933,0.925]) translate([-1080.00,-177.50,362.00]) cube([70.00,72.00,90.00]);
  color([0.541,0.561,0.600]) translate([-1070.00,-194.50,362.00]) cube([60.00,15.00,90.00]);
  color([0.541,0.561,0.600]) translate([-1070.00,-211.50,362.00]) cube([60.00,15.00,90.00]);
}
// QE-PSU#1 - Alimentatori PSU1 48 V 480 W, PSU2 24 V, PSU3 12 V
translate([0,0,0]) translate(explode*[-420,0,300]) {
  color([0.667,0.702,0.737]) translate([-1138.50,129.50,180.00]) cube([128.50,85.50,125.00]);
  color([0.667,0.702,0.737]) translate([-1064.50,-117.50,200.00]) cube([54.50,52.50,90.00]);
  color([0.667,0.702,0.737]) translate([-1064.50,-142.50,200.00]) cube([54.50,17.50,90.00]);
}
// QE-DRV#1 - Driver closed-loop CL57T U11 (X), U12 (Z1), U13 (Z2), U14 (R)
translate([0,0,0]) translate(explode*[-460,0,300]) {
  color([0.169,0.184,0.200]) translate([-1085.50,81.00,185.00]) cube([75.50,34.00,118.00]);
  color([0.165,0.604,0.227]) translate([-1087.00,85.00,290.00]) cube([77.00,26.00,10.00]);
  color([0.165,0.604,0.227]) translate([-1087.00,85.00,190.00]) cube([77.00,26.00,10.00]);
  color([0.169,0.184,0.200]) translate([-1085.50,36.00,185.00]) cube([75.50,34.00,118.00]);
  color([0.165,0.604,0.227]) translate([-1087.00,40.00,290.00]) cube([77.00,26.00,10.00]);
  color([0.165,0.604,0.227]) translate([-1087.00,40.00,190.00]) cube([77.00,26.00,10.00]);
  color([0.169,0.184,0.200]) translate([-1085.50,-9.00,185.00]) cube([75.50,34.00,118.00]);
  color([0.165,0.604,0.227]) translate([-1087.00,-5.00,290.00]) cube([77.00,26.00,10.00]);
  color([0.165,0.604,0.227]) translate([-1087.00,-5.00,190.00]) cube([77.00,26.00,10.00]);
  color([0.169,0.184,0.200]) translate([-1085.50,-54.00,185.00]) cube([75.50,34.00,118.00]);
  color([0.165,0.604,0.227]) translate([-1087.00,-50.00,290.00]) cube([77.00,26.00,10.00]);
  color([0.165,0.604,0.227]) translate([-1087.00,-50.00,190.00]) cube([77.00,26.00,10.00]);
}
// QE-BPE#1 - Barra di terra BPE
translate([0,0,0]) translate(explode*[-340,0,300]) {
  color([0.345,0.635,0.227]) translate([-1035.00,-215.00,162.00]) cube([25.00,65.00,10.00]);
}
// QE-LOG#1 - Logica: Arduino Mega + Ethernet (A1), opto U6/U7, relè U8, DC/DC U9, morsetti X3/X4/X6/X7
translate([0,0,0]) translate(explode*[-260,140,300]) {
  color([0.059,0.498,0.525]) translate([-1141.60,-248.00,390.00]) cube([101.60,32.00,53.30]);
  color([0.184,0.227,0.267]) translate([-1116.00,-248.00,396.00]) cube([70.00,40.00,40.00]);
  color([0.114,0.373,0.659]) translate([-1112.00,-248.00,305.00]) cube([72.00,18.00,50.00]);
  color([0.114,0.373,0.659]) translate([-1202.00,-248.00,305.00]) cube([72.00,18.00,50.00]);
  color([0.114,0.373,0.659]) translate([-1115.00,-248.00,225.00]) cube([75.00,22.00,55.00]);
  color([0.165,0.384,0.788]) translate([-1105.00,-248.00,235.00]) cube([55.00,38.00,35.00]);
  color([0.667,0.702,0.737]) translate([-1150.00,-248.00,225.00]) cube([20.00,25.00,55.00]);
  color([0.541,0.561,0.600]) translate([-1210.00,-248.00,225.00]) cube([45.00,40.00,55.00]);
  color([0.541,0.561,0.600]) translate([-1120.00,-248.00,155.00]) cube([80.00,45.00,40.00]);
  color([0.247,0.435,0.710]) translate([-1210.00,-248.00,155.00]) cube([80.00,45.00,40.00]);
}
// QE-FAN#1 - Ventola filtrata 120 mm e griglia di uscita
translate([0,0,0]) translate(explode*[-260,-100,300]) {
  color([0.227,0.251,0.282]) translate([-1195.00,218.00,350.00]) cube([120.00,30.00,120.00]);
  color([0.349,0.380,0.420]) translate([-1135.00,232.00,410.00]) rotate([-90,0,0]) cylinder(r=55.00, h=6.00, center=true);
  color([0.349,0.380,0.420]) translate([-1195.00,236.00,130.00]) cube([120.00,12.00,120.00]);
}
