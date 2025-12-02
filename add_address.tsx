// app/add_address.tsx
import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  PixelRatio,
  TextInput,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter, useLocalSearchParams } from 'expo-router';
import MapView, { Marker, UrlTile } from 'react-native-maps';

const { width, height } = Dimensions.get('window');

// MapTiler key
const MAPTILER_KEY = 'ER8AcLONjNZgjTKFnSW1';

function getMapTilerUrlTemplate() {
  const dpr = PixelRatio.get();
  if (dpr >= 2) {
    return `https://api.maptiler.com/maps/streets-v4/{z}/{x}/{y}.png?key=${MAPTILER_KEY}`;
  }
  return `https://api.maptiler.com/maps/streets-v4/256/{z}/{x}/{y}.png?key=${MAPTILER_KEY}`;
}

/** ---------- Floating label input (label moves OUTSIDE on focus/value) ---------- **/
type FloatingProps = {
  label: string;
  value: string;
  onChangeText?: (text: string) => void;
  keyboardType?: 'default' | 'numeric';
  editable?: boolean;
  containerStyle?: any;
  inputContainerStyle?: any;
  showDropdownIcon?: boolean; // for State / District
};

const FloatingLabelInput: React.FC<FloatingProps> = ({
  label,
  value,
  onChangeText = () => {},
  keyboardType = 'default',
  editable = true,
  containerStyle,
  inputContainerStyle,
  showDropdownIcon = false,
}) => {
  const [focused, setFocused] = useState(false);
  const showFloatingLabel = focused || !!value; // when focused or has text

  // validation

  return (
    <View style={[styles.floatingWrapper, containerStyle]}>
      {/* Label OUTSIDE the box when active */}
      {showFloatingLabel && (
        <Text style={styles.floatingLabel}>{label}</Text>
      )}

      <View style={[styles.floatingContainer, inputContainerStyle]}>
        <TextInput
          style={[
            styles.floatingInput,
            !editable && styles.floatingInputDisabled,
            showDropdownIcon && { paddingRight: width * 0.08 },
          ]}
          value={value}
          onChangeText={onChangeText}
          placeholder={showFloatingLabel ? '' : label} // text inside box initially
          placeholderTextColor="#999"
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          keyboardType={keyboardType}
          editable={editable}
        />

        {showDropdownIcon && (
          <Ionicons
            name="chevron-down"
            size={width * 0.035}
            color="#666"
            style={styles.dropdownIcon}
          />
        )}
      </View>
    </View>
  );
};

/** ------------------------- Screen ------------------------- **/

const AddAddressScreen = () => {
  const router = useRouter();

  // receive coords + address + state/district/pincode from previous page
  const params = useLocalSearchParams<{
    latitude?: string;
    longitude?: string;
    address?: string;
    subAddress?: string;
    state?: string;
    district?: string;
    pincode?: string;
  }>();

  const latitude = parseFloat(params.latitude ?? '17.385');
  const longitude = parseFloat(params.longitude ?? '78.4867');

  const mainAddress = params.address ?? 'Selected location';
  const subtitle = params.subAddress ?? '';

  const [stateValue, setStateValue] = useState(params.state ?? '');
  const [districtValue, setDistrictValue] = useState(params.district ?? '');
  const [pincodeValue, setPincodeValue] = useState(params.pincode ?? '');
  const [apartment, setApartment] = useState('');
  const [landmark, setLandmark] = useState('');
  const isFormValid =
  apartment.trim() !== "" &&
  landmark.trim() !== "" &&
  stateValue.trim() !== "" &&
  districtValue.trim() !== "" &&
  pincodeValue.trim() !== "";



  const urlTemplate = getMapTilerUrlTemplate();

  const handleSaveAddress = () => {
  // build a single string for the full address
  const parts = [
    apartment,
    landmark,
    mainAddress,
    subtitle,
    districtValue,
    stateValue,
    pincodeValue,
  ].filter((p) => p && p.trim().length > 0);

  const fullAddress = parts.join(", ");


  // 👉 navigate back to Cart and send this new address
  router.push({
    pathname: "/cart",      // adjust if your file is in a different route
    params: {
      newAddress: fullAddress,
    },
  });
};


  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.headerContainer}>
        <TouchableOpacity
          style={styles.backButton}
          onPress={() => router.back()}
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <Ionicons name="arrow-back" size={width * 0.06} color="#000" />
        </TouchableOpacity>

        <Text style={styles.headerTitle}>Add Address Details</Text>
        <View style={styles.rightPlaceholder} />
      </View>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        {/* Map preview */}
        <View style={styles.mapWrapper}>
          <MapView
            style={styles.map}
            pointerEvents="none"
            mapType="none" 
            initialRegion={{
              latitude,
              longitude,
              latitudeDelta: 0.01,
              longitudeDelta: 0.01,
            }}
          >
            <UrlTile urlTemplate={urlTemplate} maximumZ={18} />
            <Marker coordinate={{ latitude, longitude }} />
          </MapView>
        </View>

        {/* Address + Change row */}
        <View style={styles.addressRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.addressTitle}>{mainAddress}</Text>
            <Text style={styles.addressSubtitle} numberOfLines={1}>
              {subtitle}
            </Text>
          </View>

          <TouchableOpacity
            style={styles.changeButton}
            onPress={() => router.back()}
          >
            <Text style={styles.changeButtonText}>Change</Text>
          </TouchableOpacity>
        </View>

        {/* Form section */}
        <FloatingLabelInput
          label="Apartment Name/H.No/Flat No."
          value={apartment}
          onChangeText={setApartment}
          containerStyle={{ marginTop: height * 0.025}}
          inputContainerStyle={{ height: height * 0.08 }}
        />

        <FloatingLabelInput
          label="Landmark"
          value={landmark}
          onChangeText={setLandmark}
          inputContainerStyle={{ height: height * 0.08 }}
        />

        <View style={styles.row}>
          <FloatingLabelInput
            label="State"
            value={stateValue}
            onChangeText={setStateValue}
            containerStyle={{ flex: 1, marginRight: width * 0.02 }}
            showDropdownIcon
          />
          <FloatingLabelInput
            label="District"
            value={districtValue}
            onChangeText={setDistrictValue}
            containerStyle={{ flex: 1, marginLeft: width * 0.02 }}
            showDropdownIcon
          />
        </View>

        <FloatingLabelInput
          label="PINCODE"
          value={pincodeValue}
          onChangeText={setPincodeValue}
          keyboardType="numeric"
        />

        {/* Save button */}
        <TouchableOpacity
  style={[
    styles.saveButton,
    !isFormValid && { opacity: 0.5 }, // dim when disabled
  ]}
  onPress={handleSaveAddress}
  disabled={!isFormValid}
>
  <Text style={styles.saveButtonText}>Save Address</Text>
</TouchableOpacity>

      </ScrollView>
    </SafeAreaView>
  );
};

export default AddAddressScreen;

/** ------------------------- Styles ------------------------- **/

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },

  headerContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: width * 0.04,
    paddingTop: height * 0.015,
    paddingBottom: height * 0.015,
    marginTop: height * 0.02,
  },
  backButton: {
    width: width * 0.06,
    justifyContent: 'center',
    alignItems: 'flex-start',
  },
  headerTitle: {
    flex: 1,
    textAlign: 'center',
    fontSize: width * 0.042,
    fontWeight: '500',
    color: '#000',
  },
  rightPlaceholder: {
    width: width * 0.06,
  },

  scrollContent: {
    paddingHorizontal: width * 0.05,
    paddingBottom: height * 0.04,
  },

  mapWrapper: {
    marginTop: height * 0.03,
    borderRadius: 12,
    overflow: 'hidden',
    height: height * 0.27,
  },
  map: {
    width: '100%',
    height: '100%',
  },

  addressRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: height * 0.02,
    marginBottom: height * 0.02,
  },
  addressTitle: {
    fontSize: width * 0.04,
    fontWeight: '600',
    color: '#000',
    marginBottom: height * 0.003,
  },
  addressSubtitle: {
    fontSize: width * 0.032,
    color: '#666',
  },
  changeButton: {
    paddingHorizontal: width * 0.03,
    paddingVertical: height * 0.006,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#b0adadff',
    marginLeft: width * 0.02,
    width: width * 0.2,
    alignItems: 'center',
  },
  changeButtonText: {
    fontSize: width * 0.032,
    color: '#000',
    fontWeight: '600',
    fontFamily: 'LeagueSpartan-Regular',
  },

  /* Floating label system */
  floatingWrapper: {
    marginTop: height * 0.03,
    marginLeft: width * 0.04,
    marginRight: width * 0.04,
  },
  floatingLabel: {
    position: 'absolute',
    left: width * 0.025,   // aligns with inner text
    top: -16,
    fontSize: 12,
    color: '#999',
    backgroundColor: '#fff',
    paddingHorizontal: 4,
  },
  floatingContainer: {
    borderWidth: 1,
    borderColor: '#bfbfbf',
    borderRadius: 9,
    paddingHorizontal: width * 0.025, // smaller → less side gap
    height: height * 0.065,           // tuned height
    justifyContent: 'center',
  },
  floatingInput: {
    fontSize: width * 0.034,
    color: '#000',
    padding: 0,
    textAlignVertical: 'center',      // Android: vertical centering
  },
  floatingInputDisabled: {
    color: '#555',
  },
  dropdownIcon: {
    position: 'absolute',
    right: width * 0.03,
    top: '50%',
    marginTop: -width * 0.017,
  },

  row: {
    flexDirection: 'row',
    marginTop: height * 0.012,
  },

  saveButton: {
    marginTop: height * 0.03,
    backgroundColor: '#CAFFE2',
    borderRadius: 10,
    paddingVertical: height * 0.017,
    alignItems: 'center',
    marginLeft: width * 0.04,
    marginRight: width * 0.04,
  },
  saveButtonText: {
    fontSize: width * 0.04,
    color: '#000',
    fontWeight: '500',
  },
});
