#include "DiscreteCoverageChecker.hpp"

std::vector<AnglePair> DiscreteCoverageChecker::unitVectorToClockCone(const std::vector<Rvector3> &cartesianHeadings)
{
	int numPts = cartesianHeadings.size();
	std::vector<std::array<Real,2>> clockConeHeadings(numPts);
	for(int i = 0;i < numPts;i++)
	{
		// Returns Rvector3 of lat,lon,H
		Rvector3 spherical = BodyFixedStateConverterUtil::CartesianToSpherical(cartesianHeadings[i],1.0,1.0);
		clockConeHeadings[i] = {spherical[1],pi/2 - spherical[0]};
	}
	return clockConeHeadings;
}

AnglePair DiscreteCoverageChecker::projectionAlg(Real clock,Real cone,const Rvector3 &sphericalPos)
{
	Real r,latSSP,lonSSP,H;
	Real sinRho,epsilon,lambda,phiE,latPPrime,lonP,latP,deltaL;
	AnglePair latLonP;
	
	r = centralBody->GetRadius();
	latSSP = sphericalPos[0];
	lonSSP = sphericalPos[1];
	H = sphericalPos[2];
	
	sinRho = r/(r + H);

	epsilon = acos(sin(cone)/sinRho);

	lambda = (pi/2) - cone - epsilon;
	phiE = -clock;

	latPPrime = acos(cos(lambda)*sin(latSSP) + sin(lambda)*cos(latSSP)*cos(phiE));
	latP = pi/2 - latPPrime;

	deltaL = acos( (cos(lambda) - sin(latSSP)*sin(latP))/(cos(latSSP)*cos(latP)));
	
	if(clock < pi)
		lonP = lonSSP + deltaL;
	else
		lonP = lonSSP - deltaL;
		
	latLonP = {latP,lonP};
	
	return latLonP;
}

/*
// Cone here is cone angle to edge!
std::array<Real,3> DiscreteCoverageChecker::poleProjectionAlg(Real clock,Real cone,const Rvector3 &sphericalPos)
{
	Real r,latSSP,lonSSP,H;
	Real lambda,phiE,latPPrime,lonP,latP,deltaL;
	std::array<Real,3> pole;
	
	Real cosZeta,zeta;
	
	r = centralBody->GetRadius();
	latSSP = sphericalPos[0];
	lonSSP = sphericalPos[1];
	H = sphericalPos[2];
	
	cosZeta = (r + H)*sin(cone)/r;
	zeta = acos(cosZeta);

	lambda = cone + zeta;
	phiE = -clock;

	latPPrime = acos(cos(lambda)*sin(latSSP) + sin(lambda)*cos(latSSP)*cos(phiE));
	latP = pi/2 - latPPrime;

	deltaL = acos( (cos(lambda) - sin(latSSP)*sin(latP))/(cos(latSSP)*cos(latP)));
	
	if(clock < pi)
		lonP = lonSSP + deltaL;
	else
		lonP = lonSSP - deltaL;
		
	pole = {latP,lonP,zeta};
	
	return pole;
}
*/

Rmatrix33 DiscreteCoverageChecker::getNadirToSpacecraftAccessMatrix(const Rvector6 &state_ECF)
{
	Rvector3 pos_ECF(state_ECF[0],state_ECF[1],state_ECF[2]);   
	Rvector3 vel_ECF(state_ECF[3],state_ECF[4],state_ECF[5]);
	
	Rvector3 sphericalPos_ECF = BodyFixedStateConverterUtil::CartesianToSpherical(pos_ECF,1,centralBody->GetRadius());

	Rvector3 vel_T= centralBody->FixedToTopocentric(vel_ECF,sphericalPos_ECF[0],sphericalPos_ECF[1]);
	
	// Transform velocity vector to Spacecraft Access coordinates and normalize
	vel_T[0] = -vel_T[0];
	vel_T[2] = -vel_T[2];
	vel_T.Normalize();
	
	// Construct SA-N
	Rvector3 zHat(0,0,1);
	Rvector3 xHat = Cross(vel_T,zHat);
	
	Rmatrix33 SA_N(xHat[0],vel_T[0],zHat[0],xHat[1],vel_T[1],zHat[1],xHat[2],vel_T[2],zHat[2]);
	
	return SA_N;
}

DiscreteCoverageChecker::DiscreteCoverageChecker(Spacecraft *satIn,DiscretizedSensor *sensorIn) :
	sc(satIn),
	sensor(sensorIn)
{
	centralBody = new Earth();
}

Rvector6 DiscreteCoverageChecker::getEarthFixedState(Real jd,const Rvector6& state_I)
{
	// Converts state from Earth interial to Earth fixed
	Rvector3 inertialPos   = state_I.GetR();
	Rvector3 inertialVel   = state_I.GetV();
	// TODO.  Handle differences in units of points and states.
	// TODO.  This ignores omega cross r term in velocity, which is ok and 
	// perhaps desired for current use cases but is not always desired.
	Rvector3 centralBodyFixedPos  = centralBody->GetBodyFixedState(inertialPos,jd);
	Rvector3 centralBodyFixedVel  = centralBody->GetBodyFixedState(inertialVel,
                                                                  jd);
                                                                  
	Rvector6 earthFixedState(centralBodyFixedPos(0), centralBodyFixedPos(1),
                            centralBodyFixedPos(2),
                            centralBodyFixedVel(0), centralBodyFixedVel(1),
                            centralBodyFixedVel(2));
                            
	return earthFixedState;
}

std::vector<AnglePair> DiscreteCoverageChecker::checkIntersection()
{
	Real date = sc->GetJulianDate();
	Rvector6 state_I = sc->GetCartesianState();
	Rvector6 state_ECF  = getEarthFixedState(date, state_I);
	return checkIntersection(state_ECF);
}

std::vector<AnglePair> DiscreteCoverageChecker::checkIntersection(const Rvector6 &state_ECF)
{
	// In Sensor Frame
	std::vector<Rvector3> cartesianHeadings = sensor->getCartesianHeadings();
	
	int numPts = cartesianHeadings.size();
	std::vector<AnglePair> latLonVector(numPts);
	
	// Both in ECF coordinates
	Rvector3 pos(state_ECF[0],state_ECF[1],state_ECF[2]);
	Rvector3 sphericalPos = BodyFixedStateConverterUtil::CartesianToSpherical(pos,1,centralBody->GetRadius());
	
	// Only works for one sensor!
	Rmatrix33 BS = sensor->GetBodyToSensorMatrix(0).Transpose();
	Rmatrix33 NB = sc->GetNadirTOBodyMatrix().Transpose();
	Rmatrix33 SA_N = getNadirToSpacecraftAccessMatrix(state_ECF);
	
	// Change heading basis to 'Spacecraft Access (SA)' frame
	for(int i = 0;i < numPts;i++)
	{
		// In Spacecraft Access frame
		cartesianHeadings[i] = SA_N*NB*BS*cartesianHeadings[i];
	}
	
	std::vector<AnglePair> clockConeHeadings = unitVectorToClockCone(cartesianHeadings);
	
	for(int i = 0;i < numPts;i++)
	{
		latLonVector[i] = projectionAlg(clockConeHeadings[i][0],clockConeHeadings[i][1],sphericalPos);
	}
	
	return latLonVector;
}

std::vector<Rvector3> DiscreteCoverageChecker::checkPoleIntersection(const Rvector6 &state_ECF)
{
	// In Sensor Frame
	std::vector<Rvector3> poleHeadings = sensor->getPoleHeadings();
	
	int numPts = poleHeadings.size();
	
	// Only works for one sensor!
	Rmatrix33 BS = sensor->GetBodyToSensorMatrix(0).Transpose();
	Rmatrix33 NB = sc->GetNadirTOBodyMatrix().Transpose();
	Rmatrix33 ECF_N = sc->GetBodyFixedToReference(state_ECF).Transpose();
	
	// Change heading basis to Earth Fixed frame
	for(int i = 0;i < numPts;i++)
	{
		// In ECF coordinates
		poleHeadings[i] = ECF_N*NB*BS*poleHeadings[i];
		// Re-normalize
		poleHeadings[i].Normalize();
	}
	return poleHeadings;
}

std::vector<AnglePair> DiscreteCoverageChecker::checkCornerIntersection(const Rvector6 &state_ECF)
{
	// In Sensor Frame
	std::vector<Rvector3> cornerHeadings = sensor->getCornerHeadings();
	
	int numPts = cornerHeadings.size();
	std::vector<AnglePair> latLonVector(numPts);
	
	// Both in ECF coordinates
	Rvector3 pos(state_ECF[0],state_ECF[1],state_ECF[2]);
	Rvector3 sphericalPos = BodyFixedStateConverterUtil::CartesianToSpherical(pos,1,centralBody->GetRadius());
	
	// Only works for one sensor!
	Rmatrix33 BS = sensor->GetBodyToSensorMatrix(0).Transpose();
	Rmatrix33 NB = sc->GetNadirTOBodyMatrix().Transpose();
	Rmatrix33 SA_N = getNadirToSpacecraftAccessMatrix(state_ECF);
	
	// Change heading basis to 'Spacecraft Access (SA)' frame
	for(int i = 0;i < numPts;i++)
	{
		// In Spacecraft Access frame
		cornerHeadings[i] = SA_N*NB*BS*cornerHeadings[i];
	}
	
	std::vector<AnglePair> clockConeHeadings = unitVectorToClockCone(cornerHeadings);
	
	for(int i = 0;i < numPts;i++)
	{
		latLonVector[i] = projectionAlg(clockConeHeadings[i][0],clockConeHeadings[i][1],sphericalPos);
	}
	
	return latLonVector;
}

/*
// Input is clock,cone of pole
Real DiscreteCoverageChecker::getPoleLambda(Real alphaP,Real delP)
{
	Real delN = 0, alphaN = 0;
	Real cThetaP = sin(delP)*sin(delN)+cos(delP)*cos(delN)*cos(alphaP - alphaN);
	Real thetaE = asin(cThetaP);
	
	return thetaE;
}

std::vector<AnglePair> DiscreteCoverageChecker::checkPoleIntersection(const Rvector6 &state_ECF)
{
	// In Sensor Frame
	std::vector<Rvector3> poleHeadings = sensor->getPoleHeadings();
	
	int numPts = poleHeadings.size();
	std::vector<std::array<Real,3>> poleVector(numPts);
	
	// Both in ECF coordinates
	Rvector3 pos(state_ECF[0],state_ECF[1],state_ECF[2]);
	Rvector3 sphericalPos = BodyFixedStateConverterUtil::CartesianToSpherical(pos,1,centralBody->GetRadius());
	
	// Only works for one sensor!
	Rmatrix33 BS = sensor->GetBodyToSensorMatrix(0).Transpose();
	Rmatrix33 NB = sc->GetNadirTOBodyMatrix().Transpose();
	Rmatrix33 SA_N = getNadirToSpacecraftAccessMatrix(state_ECF);
	
	// Change heading basis to 'Spacecraft Access (SA)' frame
	for(int i = 0;i < numPts;i++)
	{
		// In Spacecraft Access frame
		poleHeadings[i] = SA_N*NB*BS*poleHeadings[i];
	}
	
	std::vector<AnglePair> clockConeHeadings = unitVectorToClockCone(poleHeadings);
	
	for(int i = 0;i < numPts;i++)
	{
		poleVector[i] = projectionAlg(clockConeHeadings[i][0],clockConeHeadings[i][1],sphericalPos);
	}
	
	return poleVector;
}
*/
