// ManipMasta - generato da cad/model.py: non modificare a mano, rigenera.
// Parametri vista:
explode = 0;   // 0..1
xpos = 0;      // posizione X rullo (mm)
gap = 40;   // luce rullo-piano (mm)
$fn = 48;

dz = gap - 40;

// TAV - Tavolo da pasticceria (esistente)
translate([0,0,0]) translate(explode*[0,0,-250]) {
  color([0.831,0.851,0.871]) translate([-1000.00,-400.00,-40.00]) cube([2000.00,800.00,40.00]);
  color([0.604,0.635,0.671]) translate([-985.00,-385.00,-900.00]) cube([50.00,50.00,860.00]);
  color([0.604,0.635,0.671]) translate([-985.00,335.00,-900.00]) cube([50.00,50.00,860.00]);
  color([0.604,0.635,0.671]) translate([935.00,-385.00,-900.00]) cube([50.00,50.00,860.00]);
  color([0.604,0.635,0.671]) translate([935.00,335.00,-900.00]) cube([50.00,50.00,860.00]);
  color([0.604,0.635,0.671]) translate([-960.00,-360.00,-750.00]) cube([1920.00,720.00,20.00]);
}
// IMP - Palla di impasto (indicativa)
translate([0,0,0]) translate(explode*[0,0,0]) {
  color([0.902,0.769,0.541]) translate([0,0,55]) scale([110,110,55]) sphere(r=1);
}
// ANC-01 - Ancoraggio A1 riferimento Ø20 H7
translate([0,0,0]) translate(explode*[0,0,60]) {
  color([0.427,0.478,0.529]) translate([-980.00,-390.00,0.00]) cube([100.00,100.00,50.00]);
  color([0.200,0.227,0.259]) translate([-930.00,-340.00,50.50]) rotate([0,0,0]) cylinder(r=10.00, h=1.00, center=true);
}
// ANC-02 - Ancoraggio A2 asola 20 H7×26
translate([0,0,0]) translate(explode*[0,0,60]) {
  color([0.427,0.478,0.529]) translate([880.00,-390.00,0.00]) cube([100.00,100.00,50.00]);
  color([0.200,0.227,0.259]) translate([930.00,-340.00,50.50]) rotate([0,0,0]) cylinder(r=13.00, h=1.00, center=true);
}
// ANC-03 - Ancoraggio A3 appoggio Ø26
translate([0,0,0]) translate(explode*[0,0,60]) {
  color([0.427,0.478,0.529]) translate([-980.00,290.00,0.00]) cube([100.00,100.00,50.00]);
  color([0.200,0.227,0.259]) translate([-930.00,340.00,50.50]) rotate([0,0,0]) cylinder(r=13.00, h=1.00, center=true);
}
// ANC-03 - Ancoraggio A4 appoggio Ø26
translate([0,0,0]) translate(explode*[0,0,60]) {
  color([0.427,0.478,0.529]) translate([880.00,290.00,0.00]) cube([100.00,100.00,50.00]);
  color([0.200,0.227,0.259]) translate([930.00,340.00,50.50]) rotate([0,0,0]) cylinder(r=13.00, h=1.00, center=true);
}
// TEL-01 - Telaio portale saldato
translate([0,0,0]) translate(explode*[0,0,320]) {
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
// PER-01 - Perni di centraggio Ø20 g6 (×4)
translate([0,0,0]) translate(explode*[0,0,200]) {
  color([0.541,0.580,0.624]) translate([-930.00,-340.00,32.50]) rotate([0,0,0]) cylinder(r=10.00, h=35.00, center=true);
  color([0.541,0.580,0.624]) translate([-930.00,340.00,32.50]) rotate([0,0,0]) cylinder(r=10.00, h=35.00, center=true);
  color([0.541,0.580,0.624]) translate([930.00,-340.00,32.50]) rotate([0,0,0]) cylinder(r=10.00, h=35.00, center=true);
  color([0.541,0.580,0.624]) translate([930.00,340.00,32.50]) rotate([0,0,0]) cylinder(r=10.00, h=35.00, center=true);
}
// SEN-SEAT - Sensori induttivi M12 'portale in sede' (×2)
translate([0,0,0]) translate(explode*[0,0,330]) {
  color([0.878,0.690,0.000]) translate([-885.00,-385.00,85.00]) rotate([0,0,0]) cylinder(r=6.00, h=50.00, center=true);
  color([0.878,0.690,0.000]) translate([975.00,-385.00,85.00]) rotate([0,0,0]) cylinder(r=6.00, h=50.00, center=true);
}
// SBR20 - Guide supportate SBR20 L=1800 (×2)
translate([0,0,0]) translate(explode*[0,0,420]) {
  color([0.239,0.271,0.314]) translate([-900.00,-360.00,470.00]) cube([1800.00,40.00,18.00]);
  color([0.788,0.808,0.831]) translate([0.00,-340.00,497.00]) rotate([0,90,0]) cylinder(r=10.00, h=1800.00, center=true);
  color([0.239,0.271,0.314]) translate([-900.00,320.00,470.00]) cube([1800.00,40.00,18.00]);
  color([0.788,0.808,0.831]) translate([0.00,340.00,497.00]) rotate([0,90,0]) cylinder(r=10.00, h=1800.00, center=true);
}
// SBR20UU - Pattini SBR20UU (×4)
translate([xpos,0,0]) translate(explode*[0,0,470]) {
  color([0.184,0.427,0.690]) translate([-100.00,-364.00,488.00]) cube([50.00,48.00,35.00]);
  color([0.184,0.427,0.690]) translate([50.00,-364.00,488.00]) cube([50.00,48.00,35.00]);
  color([0.184,0.427,0.690]) translate([-100.00,316.00,488.00]) cube([50.00,48.00,35.00]);
  color([0.184,0.427,0.690]) translate([50.00,316.00,488.00]) cube([50.00,48.00,35.00]);
}
// CAR-01 - Piastra carrello X lato Y−
translate([xpos,0,0]) translate(explode*[0,0,560]) {
  color([0.773,0.800,0.827]) translate([-125.00,-340.00,523.00]) cube([250.00,150.00,12.00]);
  color([0.773,0.800,0.827]) translate([-80.00,-390.00,463.00]) cube([40.00,10.00,60.00]);
}
// CAR-01 - Piastra carrello X lato Y+
translate([xpos,0,0]) translate(explode*[0,0,560]) {
  color([0.773,0.800,0.827]) translate([-125.00,190.00,523.00]) cube([250.00,150.00,12.00]);
  color([0.773,0.800,0.827]) translate([-80.00,380.00,463.00]) cube([40.00,10.00,60.00]);
}
// PON-01 - Traversa ponte 40×40×2
translate([xpos,0,0]) translate(explode*[0,0,640]) {
  color([0.725,0.753,0.784]) translate([-120.00,-415.00,535.00]) cube([40.00,830.00,40.00]);
}
// ZPL-01 - Piastra Z fissa lato Y−
translate([xpos,0,0]) translate(explode*[0,-140,560]) {
  color([0.773,0.800,0.827]) translate([-150.00,-265.00,140.00]) cube([300.00,15.00,395.00]);
}
// ZGD - Guide Ø16 + vite TR16×4 lato Y−
translate([xpos,0,0]) translate(explode*[0,-90,600]) {
  color([0.788,0.808,0.831]) translate([-100.00,-242.00,342.50]) rotate([0,0,0]) cylinder(r=8.00, h=365.00, center=true);
  color([0.788,0.808,0.831]) translate([100.00,-242.00,342.50]) rotate([0,0,0]) cylinder(r=8.00, h=365.00, center=true);
  color([0.561,0.561,0.561]) translate([75.00,-242.00,352.50]) rotate([0,0,0]) cylinder(r=8.00, h=405.00, center=true);
}
// MOT-Z - Motore Z1 NEMA23 closed-loop
translate([xpos,0,0]) translate(explode*[0,-90,760]) {
  color([0.141,0.153,0.169]) translate([46.50,-270.50,545.00]) cube([57.00,57.00,100.00]);
  color([0.604,0.631,0.659]) translate([55.00,-262.00,645.00]) cube([40.00,40.00,4.00]);
  color([0.773,0.800,0.827]) translate([30.00,-282.00,535.00]) cube([90.00,80.00,10.00]);
}
// ZSL-01 - Slitta Z lato Y−
translate([xpos,0,dz]) translate(explode*[0,-200,360]) {
  color([0.773,0.800,0.827]) translate([-140.00,-234.00,45.00]) cube([280.00,12.00,230.00]);
  color([0.184,0.427,0.690]) translate([-117.00,-257.00,222.50]) cube([34.00,30.00,45.00]);
  color([0.184,0.427,0.690]) translate([83.00,-257.00,222.50]) cube([34.00,30.00,45.00]);
  color([0.690,0.553,0.227]) translate([55.00,-257.00,210.00]) cube([40.00,30.00,30.00]);
}
// SUCF204 - Supporto flangiato inox SUCF204 lato Y−
translate([xpos,0,dz]) translate(explode*[0,-260,300]) {
  color([0.498,0.545,0.592]) translate([-43.00,-222.00,47.00]) cube([86.00,24.00,86.00]);
  color([0.725,0.753,0.784]) translate([0.00,-196.00,90.00]) rotate([-90,0,0]) cylinder(r=20.00, h=8.00, center=true);
}
// ZPL-01 - Piastra Z fissa lato Y+
translate([xpos,0,0]) translate(explode*[0,140,560]) {
  color([0.773,0.800,0.827]) translate([-150.00,250.00,140.00]) cube([300.00,15.00,395.00]);
}
// ZGD - Guide Ø16 + vite TR16×4 lato Y+
translate([xpos,0,0]) translate(explode*[0,90,600]) {
  color([0.788,0.808,0.831]) translate([-100.00,242.00,342.50]) rotate([0,0,0]) cylinder(r=8.00, h=365.00, center=true);
  color([0.788,0.808,0.831]) translate([100.00,242.00,342.50]) rotate([0,0,0]) cylinder(r=8.00, h=365.00, center=true);
  color([0.561,0.561,0.561]) translate([75.00,242.00,352.50]) rotate([0,0,0]) cylinder(r=8.00, h=405.00, center=true);
}
// MOT-Z - Motore Z2 NEMA23 closed-loop
translate([xpos,0,0]) translate(explode*[0,90,760]) {
  color([0.141,0.153,0.169]) translate([46.50,213.50,545.00]) cube([57.00,57.00,100.00]);
  color([0.604,0.631,0.659]) translate([55.00,222.00,645.00]) cube([40.00,40.00,4.00]);
  color([0.773,0.800,0.827]) translate([30.00,202.00,535.00]) cube([90.00,80.00,10.00]);
}
// ZSL-01 - Slitta Z lato Y+
translate([xpos,0,dz]) translate(explode*[0,200,360]) {
  color([0.773,0.800,0.827]) translate([-140.00,222.00,45.00]) cube([280.00,12.00,230.00]);
  color([0.184,0.427,0.690]) translate([-117.00,227.00,222.50]) cube([34.00,30.00,45.00]);
  color([0.184,0.427,0.690]) translate([83.00,227.00,222.50]) cube([34.00,30.00,45.00]);
  color([0.690,0.553,0.227]) translate([55.00,227.00,210.00]) cube([40.00,30.00,30.00]);
}
// SUCF204 - Supporto flangiato inox SUCF204 lato Y+
translate([xpos,0,dz]) translate(explode*[0,260,300]) {
  color([0.498,0.545,0.592]) translate([-43.00,198.00,47.00]) cube([86.00,24.00,86.00]);
  color([0.725,0.753,0.784]) translate([0.00,196.00,90.00]) rotate([-90,0,0]) cylinder(r=20.00, h=8.00, center=true);
}
// RUL-01 - Rullo Ø100 L=370 con perni Ø20
translate([xpos,0,dz]) translate(explode*[0,0,240]) {
  color([0.933,0.945,0.957]) translate([0.00,0.00,90.00]) rotate([-90,0,0]) cylinder(r=50.00, h=370.00, center=true);
  color([0.725,0.753,0.784]) translate([0.00,-222.50,90.00]) rotate([-90,0,0]) cylinder(r=10.00, h=75.00, center=true);
  color([0.725,0.753,0.784]) translate([0.00,222.50,90.00]) rotate([-90,0,0]) cylinder(r=10.00, h=75.00, center=true);
}
// RAS-01 - Raschietto POM-C a molla
translate([xpos,0,dz]) translate(explode*[-120,0,300]) {
  color([0.953,0.945,0.918]) translate([-61.00,-180.00,95.00]) cube([10.00,360.00,40.00]);
}
// MOT-R - Motore R (rotazione rullo) + cinghia HTD-5M 20T→40T
translate([xpos,0,dz]) translate(explode*[0,120,420]) {
  color([0.141,0.153,0.169]) translate([0.00,-240.00,225.00]) rotate([-90,0,0]) cylinder(r=28.50, h=0.10, center=true);
  color([0.141,0.153,0.169]) translate([-28.50,-222.00,196.50]) cube([57.00,100.00,57.00]);
  color([0.655,0.678,0.702]) translate([0.00,-242.00,225.00]) rotate([-90,0,0]) cylinder(r=16.00, h=18.00, center=true);
  color([0.655,0.678,0.702]) translate([0.00,-242.00,90.00]) rotate([-90,0,0]) cylinder(r=32.00, h=18.00, center=true);
  color([0.082,0.082,0.082]) translate([-31.50,-249.50,90.00]) cube([3.00,15.00,135.00]);
  color([0.082,0.082,0.082]) translate([28.50,-249.50,90.00]) cube([3.00,15.00,135.00]);
}
// TRX-01 - Trasmissione X: albero Ø16, pulegge HTD-5M 20T, cinghie 15 mm
translate([0,0,0]) translate(explode*[0,0,380]) {
  color([0.561,0.561,0.561]) translate([-870.00,0.00,430.00]) rotate([-90,0,0]) cylinder(r=8.00, h=870.00, center=true);
  color([0.655,0.678,0.702]) translate([-870.00,-375.00,430.00]) rotate([-90,0,0]) cylinder(r=16.00, h=20.00, center=true);
  color([0.655,0.678,0.702]) translate([870.00,-375.00,430.00]) rotate([-90,0,0]) cylinder(r=16.00, h=20.00, center=true);
  color([0.082,0.082,0.082]) translate([-870.00,-382.50,445.00]) cube([1740.00,15.00,2.00]);
  color([0.082,0.082,0.082]) translate([-870.00,-382.50,413.00]) cube([1740.00,15.00,2.00]);
  color([0.541,0.580,0.624]) translate([-900.00,-368.00,400.00]) cube([60.00,8.00,60.00]);
  color([0.541,0.580,0.624]) translate([840.00,-368.00,400.00]) cube([60.00,8.00,60.00]);
  color([0.655,0.678,0.702]) translate([-870.00,375.00,430.00]) rotate([-90,0,0]) cylinder(r=16.00, h=20.00, center=true);
  color([0.655,0.678,0.702]) translate([870.00,375.00,430.00]) rotate([-90,0,0]) cylinder(r=16.00, h=20.00, center=true);
  color([0.082,0.082,0.082]) translate([-870.00,367.50,445.00]) cube([1740.00,15.00,2.00]);
  color([0.082,0.082,0.082]) translate([-870.00,367.50,413.00]) cube([1740.00,15.00,2.00]);
  color([0.541,0.580,0.624]) translate([-900.00,360.00,400.00]) cube([60.00,8.00,60.00]);
  color([0.541,0.580,0.624]) translate([840.00,360.00,400.00]) cube([60.00,8.00,60.00]);
}
// MOT-X - Motore X NEMA23 closed-loop
translate([0,0,0]) translate(explode*[0,150,380]) {
  color([0.141,0.153,0.169]) translate([-898.50,435.00,401.50]) cube([57.00,100.00,57.00]);
  color([0.773,0.800,0.827]) translate([-910.00,425.00,390.00]) cube([80.00,10.00,80.00]);
}
// SEN-X - Finecorsa X_MIN / X_MAX induttivi M12
translate([0,0,0]) translate(explode*[0,-60,420]) {
  color([0.878,0.690,0.000]) translate([-840.00,-370.00,480.00]) rotate([0,90,0]) cylinder(r=6.00, h=40.00, center=true);
  color([0.878,0.690,0.000]) translate([840.00,-370.00,480.00]) rotate([0,90,0]) cylinder(r=6.00, h=40.00, center=true);
}
// QE-01 - Quadro elettrico inox IP65 500×400×250 + colonna luminosa
translate([0,0,0]) translate(explode*[-260,0,300]) {
  color([0.835,0.855,0.871]) translate([-1230.00,-250.00,60.00]) cube([250.00,500.00,400.00]);
  color([0.831,0.125,0.125]) translate([-1240.00,120.00,380.00]) rotate([0,90,0]) cylinder(r=20.00, h=20.00, center=true);
  color([0.165,0.604,0.227]) translate([-1236.00,-120.00,380.00]) rotate([0,90,0]) cylinder(r=11.00, h=12.00, center=true);
  color([0.125,0.125,0.125]) translate([-1236.00,-170.00,380.00]) rotate([0,90,0]) cylinder(r=11.00, h=12.00, center=true);
  color([0.188,0.627,0.251]) translate([-1020.00,-210.00,520.00]) rotate([0,0,0]) cylinder(r=20.00, h=120.00, center=true);
}
