import pandas as pd
import numpy as np
import os
import traceback


def calculate_solar_potential(locator, building_data):

    print("🚀 Starting yearly solar potential calculation...")

    try:
    
        OUT_DIR =locator.get_solar_output_folder()
        # ===============================
        # LOAD PV DATA
        # ===============================
        pv_df = pd.read_csv(locator.get_conversion_photovoltaic_panels())
        module = pv_df.iloc[0]

        module_area_m2 = module['module_area_m2']
        eta_module = module['PV_n']
        PV_th = module['PV_th']
        NOCT = module['PV_noct']

        eta_optical = 0.92
        eta_inv = 0.96
        pv_yield = 1400

        print("✅ PV module loaded")

        # ===============================
        # LOAD WEATHER
        # ===============================
        weather_data = locator.load_weather()

        weather = weather_data['weather']
        weather.index = weather_data['weather_index']
        meta = weather_data['meta']

        # Ensure required columns
        weather = weather.rename(columns=str.lower)
        weather = weather[['dni', 'ghi', 'dhi', 'temp_air']]

        latitude = meta['latitude']
        longitude = meta['longitude']
        albedo = 0.2

        print(f"📍 Location: {latitude}, {longitude}")
        print(f"⏱️ Timesteps: {len(weather)}")

        # ===============================
        # SOLAR POSITION (CEA STYLE)
        # ===============================
        time = weather.index
        n = time.dayofyear
        hour = time.hour + time.minute / 60

        delta = np.radians(23.45) * np.sin(np.radians(360 * (284 + n) / 365))
        B = np.radians(360 * (n - 81) / 365)
        EoT = 9.87*np.sin(2*B) - 7.53*np.cos(B) - 1.5*np.sin(B)

        TC = 4 * longitude + EoT
        LST = hour + TC / 60
        omega = np.radians(15 * (LST - 12))

        phi = np.radians(latitude)

        cos_theta_z = (
            np.sin(phi)*np.sin(delta) +
            np.cos(phi)*np.cos(delta)*np.cos(omega)
        )
        cos_theta_z = np.clip(cos_theta_z, -1, 1)
        zenith = np.degrees(np.arccos(cos_theta_z))

        # Azimuth
        sin_azimuth = (
            np.cos(delta) * np.sin(omega) /
            np.sin(np.radians(zenith))
        )
        sin_azimuth = np.clip(sin_azimuth, -1, 1)
        solar_azimuth = np.degrees(np.arcsin(sin_azimuth)) + 180

        solpos = pd.DataFrame({
            "zenith": zenith,
            "azimuth": solar_azimuth
        }, index=time)

        print("✅ Solar position calculated")

        # ===============================
        # OUTPUT SETUP
        # ===============================
      

        results = []

        # ===============================
        # BUILDING LOOP
        # ===============================
        print(f"🏢 Processing {len(building_data)} buildings...")

        for idx, building in building_data.items():
            try:
                print(f"\n➡️ Building {idx}")

                building_name = building.get("name", f"building_{idx}")
                roof_area = building.get("roof_area", 0)

                PACKING_FACTOR = 0.88
                SHADING_FACTOR = 0.85

                A_roof = roof_area * PACKING_FACTOR * SHADING_FACTOR

                if A_roof <= 0:
                    print("⚠️ Skipped (no usable roof)")
                    continue

                # Panels
                N_panels = np.floor(A_roof / module_area_m2)
                A_total = N_panels * module_area_m2

                # Orientation
                tilt = building.get("tilt", 10)
                azimuth_pv = building.get("azimuth", 180)

                beta = np.radians(tilt)
                gamma_p = np.radians(azimuth_pv)
                theta_z = np.radians(solpos['zenith'])
                gamma_s = np.radians(solpos['azimuth'])

                # Incidence
                cos_theta_i = (
                    np.cos(theta_z) * np.cos(beta) +
                    np.sin(theta_z) * np.sin(beta) * np.cos(gamma_s - gamma_p)
                )
                cos_theta_i = np.clip(cos_theta_i, 0, None)

                # Radiation
                G_beam = weather['dni'] * cos_theta_i
                G_diffuse = weather['dhi'] * (1 + np.cos(beta)) / 2
                G_ground = weather['ghi'] * albedo * (1 - np.cos(beta)) / 2

                GPOA = G_beam + G_diffuse + G_ground
                GPOA[GPOA < 0] = 0

                # Temperature
                T_cell = weather['temp_air'] + (NOCT - 20) / 800 * GPOA

                # Efficiency
                eta_eff = eta_module * (1 + PV_th * (T_cell - 25))

                # Power
                P_dc = A_total * GPOA * eta_eff * eta_optical
                P_dc[solpos['zenith'] > 89] = 0
                P_dc[GPOA <= 0] = 0

                P_ac = P_dc * eta_inv

                # Energy
                energy_dc = P_dc / 1000
                energy_ac = P_ac / 1000

                # total_energy = float(energy_ac.sum())
                capacity_kw = energy_dc/pv_yield
                print('capacity_kw',capacity_kw)
                # Anual_sum=capacity_kw.sum()
               

                # ===============================
                # TIME SERIES OUTPUT
                # ===============================
                results= pd.DataFrame({
                    "timestamp": weather.index,
                    "building_name": building_name,
                    "solar_potential_kWh": energy_dc,
                    "solar_capacity_kW": capacity_kw,
                    "solar_roof_area_m2": A_roof,
                    "module_area_m2": A_total,
                    "total_roof_area":roof_area,
                    "num_panels": N_panels,
                    "latitude": latitude,
                    "longitude": longitude,
                })
                  #PV_gen_kW_TOTAL = PV_gen_kWh / pv_yield
                # Save CSV per building
                filename = os.path.join(
                OUT_DIR,
                f"PV_solar_potential_building_{idx}.csv"
                )

                results.to_csv(filename, index=False)

                print("✔ Saved:", filename)

                print("✔ All buildings processed successfully.")   
               

               
            except Exception as e:
                print(f"❌ Error in building {idx}")
                traceback.print_exc()

        print("\n🎉 All buildings processed")

        return OUT_DIR

    except Exception as e:
        print("🔥 CRITICAL ERROR")
        traceback.print_exc()
        return {"error": str(e)}